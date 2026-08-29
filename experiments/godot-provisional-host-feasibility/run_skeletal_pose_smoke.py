#!/usr/bin/env python3
"""Run a disposable Godot Skeleton3D/Skin shared-pose binding smoke."""

from __future__ import annotations

import argparse
from collections import Counter
import ctypes
from copy import deepcopy
import errno
import hashlib
import importlib.util
from io import BytesIO
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any

from PIL import Image, UnidentifiedImageError


sys.dont_write_bytecode = True

EXPERIMENT_ROOT = Path(__file__).resolve().parent
NEUTRAL_RUNNER_PATH = EXPERIMENT_ROOT / "run_structural_gallery_smoke.py"
CARRIER_MODULE_PATH = EXPERIMENT_ROOT / "disposable_avatar_carrier.py"
COMMAND_MODULE_PATH = EXPERIMENT_ROOT / "disposable_semantic_pose_command.py"
CONTACT_COMMAND_MODULE_PATH = EXPERIMENT_ROOT / "disposable_semantic_contact_command.py"
PROJECTION_MODULE_PATH = EXPERIMENT_ROOT / "disposable_ck_projection.py"
PACKAGE_MODULE_PATH = EXPERIMENT_ROOT / "disposable_ck_package.py"
GODOT_SCRIPT = EXPERIMENT_ROOT / "skeletal_pose_smoke.gd"
VISIBLE_GODOT_OPT_IN = "CK_ALLOW_VISIBLE_GODOT"
_CARRIER_MODULE: Any | None = None
_COMMAND_MODULE: Any | None = None
_CONTACT_COMMAND_MODULE: Any | None = None
_PROJECTION_MODULE: Any | None = None
_PACKAGE_MODULE: Any | None = None


def _load_neutral_runner():
    spec = importlib.util.spec_from_file_location(
        "neutral_structural_gallery_smoke_for_skeletal_pose",
        NEUTRAL_RUNNER_PATH,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load existing neutral smoke runner: {NEUTRAL_RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_carrier_module():
    global _CARRIER_MODULE
    if _CARRIER_MODULE is not None:
        return _CARRIER_MODULE
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location(
        "disposable_avatar_carrier_for_skeletal_pose",
        CARRIER_MODULE_PATH,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load disposable avatar carrier: {CARRIER_MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    _CARRIER_MODULE = module
    return _CARRIER_MODULE


def _load_command_module():
    global _COMMAND_MODULE
    if _COMMAND_MODULE is not None:
        return _COMMAND_MODULE
    spec = importlib.util.spec_from_file_location(
        "disposable_semantic_pose_command_for_skeletal_pose",
        COMMAND_MODULE_PATH,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load disposable semantic pose command: {COMMAND_MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    _COMMAND_MODULE = module
    return _COMMAND_MODULE


def _load_contact_command_module():
    """Load the sibling contact-command module only for contact mode."""
    global _CONTACT_COMMAND_MODULE
    if _CONTACT_COMMAND_MODULE is not None:
        return _CONTACT_COMMAND_MODULE
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location(
        "disposable_semantic_contact_command_for_skeletal_pose",
        CONTACT_COMMAND_MODULE_PATH,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load disposable semantic contact command: {CONTACT_COMMAND_MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    _CONTACT_COMMAND_MODULE = module
    return _CONTACT_COMMAND_MODULE


def _load_projection_module():
    global _PROJECTION_MODULE
    if _PROJECTION_MODULE is not None:
        return _PROJECTION_MODULE
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location(
        "disposable_ck_projection_for_skeletal_pose",
        PROJECTION_MODULE_PATH,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load disposable CK projection: {PROJECTION_MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    _PROJECTION_MODULE = module
    return _PROJECTION_MODULE


def _load_package_module():
    """Load the supplied disposable package producer/loader without package imports."""
    global _PACKAGE_MODULE
    if _PACKAGE_MODULE is not None:
        return _PACKAGE_MODULE
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location(
        "disposable_ck_package_for_skeletal_pose",
        PACKAGE_MODULE_PATH,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load disposable CK package: {PACKAGE_MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    # The package loader's normal script import is deliberately replaced with
    # the already loaded projection module.  This keeps all package checks on
    # the exact v2 validator used by this runner and avoids a second module
    # instance with different test/runtime state.
    module._load_projection_module = _load_projection_module
    _PACKAGE_MODULE = module
    return _PACKAGE_MODULE


neutral_smoke = _load_neutral_runner()
SmokeError = neutral_smoke.SmokeError
REPOSITORY_ROOT = neutral_smoke.REPOSITORY_ROOT
PROJECT_FILE = neutral_smoke.PROJECT_FILE
LAUNCHER = neutral_smoke.LAUNCHER
EXPECTED_GODOT_VERSION = neutral_smoke.EXPECTED_GODOT_VERSION
EXPECTED_GODOT_ENGINE_VERSION_STRING = neutral_smoke.EXPECTED_GODOT_ENGINE_VERSION_STRING
DEFAULT_PROFILE_IDS = neutral_smoke.DEFAULT_PROFILE_IDS
EXPECTED_ARTIFACT_NAMES = neutral_smoke.EXPECTED_ARTIFACT_NAMES
EXPECTED_TRANSLATIONS = neutral_smoke.EXPECTED_TRANSLATIONS
BONE_COUNT = 18
PROXY_COUNT = 18
TOLERANCE = 2.0e-5
NORMAL_TOLERANCE = 3.0e-4
# Godot's Basis-to-Quaternion runtime reconstruction can add a few float32 ULPs;
# semantic command/source recipe validation remains at 1e-7 in the producer.
SEMANTIC_POSE_QUATERNION_TOLERANCE = 5.0e-7
REPORT_SCHEMA = "creature-kernel.disposable-godot-skeletal-pose-smoke.v1"
REPORT_BOUNDARY = "host_local_skeleton3d_skin_pose_binding"
CONTACT_REPORT_BOUNDARY = "experiment_local_semantic_contact_and_physical_response"
REPORT_CLAIMS = [
    "host-local Skeleton3D/Skin pose binding",
    "host-local consumption of the shared structural pose recipe",
]
CONTACT_REPORT_CLAIMS = REPORT_CLAIMS + ["experiment-local semantic proxy contact and rigid-body response"]
REPORT_FLAGS = {
    "physics_stepping": False,
    "animation": False,
    "contact": False,
    "deformation": False,
    "render_output": False,
    "adapter": False,
}
CONTACT_REPORT_FLAGS = {
    "physics_stepping": True,
    "animation": False,
    "contact": True,
    "deformation": False,
    "render_output": False,
    "adapter": False,
}
CONTACT_COMMAND_SCHEMA = "creature-kernel.disposable-semantic-contact-command.v1"
CONTACT_COMMAND_BOUNDARY = "experiment_local_contact_command_evidence_only_no_adapter_or_runtime_conformance"
CONTACT_COMMAND_ID = "probe-single-semantic-contact"
CONTACT_COMMAND_VERSION = 1
CONTACT_MAPPING_REVISION = "joint-selector-to-posed-proxy-v1"
CONTACT_PARTICIPANTS = [
    {"role": "actuator", "target_index": 0, "selector": {"kind": "joint", "role": "wrist", "anchors": ["right"]}},
    {"role": "response", "target_index": 1, "selector": {"kind": "joint", "role": "wrist", "anchors": ["left"]}},
]
CONTACT_INTERACTION = {
    "kind": "single-proxy-press-release",
    "phase_order": ["approach", "contact", "release", "exit"],
}
CONTACT_PHASE_ORDER = CONTACT_INTERACTION["phase_order"]
CONTACT_PHASE_TICKS = (24, 8, 24, 8)
CONTACT_TOTAL_TICKS = sum(CONTACT_PHASE_TICKS)
# These are the frozen zero-based posed-proxy child indices in the structural
# gallery. They are report expectations, never command fields or host inputs.
CONTACT_SHAPE_INDICES = (15, 9)
CONTACT_BONE_IDS = ("bone-joint-65d9caed4027b153", "bone-joint-6a2cae71d693ac50")
CONTACT_OWNED_PARTS = (
    {"anchors": ["right"], "kind": "part", "namespace": "main", "role": "hand"},
    {"anchors": ["left"], "kind": "part", "namespace": "main", "role": "hand"},
)
CONTACT_MAX_TICKS = 256
CONTACT_MIN_SOLVER_IMPULSE = 1.0e-5
CONTACT_MIN_NORMAL_VELOCITY_CHANGE = 1.0e-5
CONTACT_MIN_RESPONSE_DISPLACEMENT = 1.0e-5
CONTACT_SOURCE_JOINTS = (
    {"anchors": ["right"], "kind": "joint", "namespace": "main", "role": "wrist"},
    {"anchors": ["left"], "kind": "joint", "namespace": "main", "role": "wrist"},
)
CONTACT_RUNTIME_SHAPE_INDICES = (0, 0)
CONTACT_PROXY_PARTITION_RULE = "nearest eligible weighted bone, then ascending derived bone id"
CONTACT_PROXY_RADIUS_RULE = "maximum point-to-segment distance over the bone's complete primary-influence partition"

# The GDScript host emits exactly one nested contact object. These names are
# intentionally not accepted as alternate report locations or field aliases.
CONTACT_REPORT_ALIAS_KEYS = {
    "semantic_contact_evidence",
    "contact_evidence",
    "semantic_contact_command",
    "semantic_contact_probe",
    "semantic_contact_command_identity",
    "semantic_contact_targets",
    "semantic_contact_source_pose_command",
    "semantic_contact_mapping_revision",
    "semantic_contact_participants",
    "semantic_contact_interaction",
    "semantic_contact_selector_mappings",
    "semantic_contact_phase_order",
    "semantic_contact_phase_ticks",
    "semantic_contact_phase_tick_schedule",
    "semantic_contact_max_ticks",
    "semantic_contact_events",
    "semantic_contact_contact_tick_evidence",
    "semantic_contact_contact_samples",
    "semantic_contact_floors",
    "semantic_contact_physics_configuration",
    "semantic_contact_solver_impulses",
    "semantic_contact_solver_impulse",
    "semantic_contact_response",
    "semantic_contact_response_writes",
    "semantic_contact_no_scripted_response_writes",
}
CONTACT_EVIDENCE_KEYS = {
    "command_identity",
    "targets",
    "source_pose_command",
    "mapping_revision",
    "participants",
    "interaction",
    "selector_mappings",
    "phase_order",
    "phase_ticks",
    "max_ticks",
    "contact_tick_evidence",
    "physics_configuration",
    "solver_impulses",
    "response",
}
DEFORMATION_REPORT_BOUNDARY = "experiment_local_contact_driven_smooth_forearm_surface_deformation"
DEFORMATION_REPORT_CLAIM = (
    "experiment-local contact-driven smooth forearm surface deformation, exact recovery, and static replay "
    "captures of runtime read-back states"
)
RENDER_COLLISION_COHERENCE_REPORT_CLAIM = (
    "experiment-local paired runtime render-surface and rigid-collision read-back coherence"
)
DEFORMATION_REPORT_CLAIMS = CONTACT_REPORT_CLAIMS + [
    DEFORMATION_REPORT_CLAIM,
    RENDER_COLLISION_COHERENCE_REPORT_CLAIM,
]
DEFORMATION_REPORT_FLAGS = {
    "physics_stepping": True,
    "animation": False,
    "contact": True,
    "deformation": True,
    "render_output": True,
    "adapter": False,
}
DEFORMATION_SURFACE_KIND = "proxy-derived-smooth-forearm"
DEFORMATION_SURFACE_ATTACHMENT = "child-of-contact-response-body"
DEFORMATION_SURFACE_COLLISION_MODE = "rigid-selected-capsule-not-deformed"
DEFORMATION_DRIVE_KIND = "actual-contact-triggered-fixed-depth-contact-normal-projected-sleeve-falloff"
DEFORMATION_AXIAL_SEGMENTS = 16
DEFORMATION_RADIAL_SEGMENTS = 32
DEFORMATION_VERTEX_COUNT = 544
DEFORMATION_TRIANGLE_COUNT = 1024
DEFORMATION_FALLOFF_RADIUS_RATIO = 0.5
DEFORMATION_MAX_AFFECTED_FRACTION = 0.5
DEFORMATION_NORMALIZED_PEAK_DEPTH = 0.05
DEFORMATION_RECOVERY_TICK = CONTACT_TOTAL_TICKS
DEFORMATION_CAPTURE_NAMES = ("reference.png", "peak.png", "recovered.png")
DEFORMATION_CAPTURE_LABELS = ("reference", "peak", "recovered")
DEFORMATION_CAPTURE_WIDTH = 1536
DEFORMATION_CAPTURE_HEIGHT = 512
DEFORMATION_CAPTURE_MAX_BYTES = 8 * 1024 * 1024
# These decoded-pixel thresholds are integrity floors/caps, not subjective
# visibility criteria. They reject blank or one-pixel evidence while keeping
# the visual appraisal itself human-owned.
DEFORMATION_CAPTURE_MIN_UNIQUE_RGBA_PIXELS = 16
DEFORMATION_CAPTURE_MIN_NON_DOMINANT_PIXELS = 1024
DEFORMATION_CAPTURE_MIN_CHANGED_PIXELS = 256
DEFORMATION_CAPTURE_MIN_TOTAL_ABS_CHANNEL_DELTA = 4096
DEFORMATION_CAPTURE_MAX_CHANGED_PIXEL_FRACTION = 0.25
DEFORMATION_MIN_NORMAL_LINE_ALIGNMENT = 1.0 - NORMAL_TOLERANCE
DEFORMATION_MIN_CONTACT_NORMAL_CENTER_ALIGNMENT = 0.1
DEFORMATION_REPORT_ALIAS_KEYS = {
    "semantic_deformation_evidence",
    "deformation_evidence",
    "deformation_captures",
}
RENDER_COLLISION_COHERENCE_SCHEMA = "creature-kernel.disposable-godot-render-collision-coherence.v1"
RENDER_COLLISION_COHERENCE_BOUNDARY = "experiment_local_render_collision_coherence"
RENDER_COLLISION_COHERENCE_FRAME = "response_body_local_selected_capsule_side"
RENDER_COLLISION_COHERENCE_COLLISION_MODE = "rigid-selected-capsule-not-deformed"
RENDER_COLLISION_COHERENCE_FALLOFF_SOURCE = "semantic_deformation.drive.falloff_weights"
RENDER_COLLISION_COHERENCE_VERTEX_COUNT = DEFORMATION_VERTEX_COUNT
RENDER_COLLISION_COHERENCE_STATE_ORDER = ("neutral", "contact_onset", "peak", "recovery")
RENDER_COLLISION_COHERENCE_ALIAS_KEYS = {
    "semantic_render_collision_coherence_evidence",
    "render_collision_coherence",
    "render_collision_coherence_evidence",
    "semantic_collision_coherence",
    "semantic_render_collision_evidence",
}
RENDER_COLLISION_COHERENCE_KEYS = {
    "schema",
    "boundary",
    "frame",
    "collision_mode",
    "selected_capsule",
    "falloff_source",
    "vertex_count",
    "state_order",
    "states",
    "collision_geometry_drift",
}
RENDER_COLLISION_COHERENCE_STATE_KEYS = {
    "state",
    "tick",
    "phase",
    "contact",
    "contact_sample_index",
    "response_body_to_world",
    "capsule_to_body",
    "sleeve_to_body",
    "capsule",
    "vertices",
    "metrics",
}
RENDER_COLLISION_COHERENCE_CAPSULE_KEYS = {
    "endpoint_a",
    "endpoint_b",
    "radius",
    "height",
}
RENDER_COLLISION_COHERENCE_METRIC_KEYS = {
    "maximum_absolute_side_clearance",
    "maximum_outward_clearance",
    "maximum_inward_penetration",
    "outside_falloff_max_penetration",
}
RENDER_COLLISION_COHERENCE_DRIFT_KEYS = {
    "reference_state",
    "max_endpoint_a_drift",
    "max_endpoint_b_drift",
    "max_radius_drift",
    "maximum_geometry_drift",
}

# Runtime evaluation is an experiment-local paired measurement, not a product
# performance contract. Godot emits the raw record below; Python adds the
# runner release and owns target declarations, percentile calculation, and the
# final paired publication.
RUNTIME_MEASUREMENT_SCHEMA = "creature-kernel.disposable-godot-runtime-measurement.v1"
RUNTIME_MEASUREMENT_BOUNDARY = "experiment_local_runtime_measurement_only"
RUNTIME_MEASUREMENT_MODES = ("cpu_deformation", "rigid_contact_only")
RUNTIME_MEASUREMENT_PHYSICS_SAMPLE_COUNT = 64
RUNTIME_MEASUREMENT_TARGETS = {
    "physics_hz": 60,
    "nominal_physics_interval_usec": 16667,
    "p95_physics_interval_screen_usec": 20000,
    "p95_cpu_deformation_update_screen_usec": 2000,
}
RUNTIME_MEASUREMENT_KEYS = {
    "schema",
    "boundary",
    "mode",
    "godot",
    "os",
    "cpu",
    "renderer",
    "adapter",
    "physics",
    "memory",
    "physics_timestamp_points",
    "cpu_deformation_updates",
}
RUNTIME_MEASUREMENT_FINAL_KEYS = RUNTIME_MEASUREMENT_KEYS | {"runner_os_uname_release"}
RUNTIME_MEASUREMENT_GODOT_KEYS = {"version", "engine_version_string"}
RUNTIME_MEASUREMENT_OS_KEYS = {"name", "distribution_name", "version", "model_name", "architecture"}
RUNTIME_MEASUREMENT_CPU_KEYS = {"processor_name", "processor_count"}
RUNTIME_MEASUREMENT_RENDERER_KEYS = {
    "method",
    "driver_name",
    "requested_display_driver",
    "actual_display_server",
    "window_size_pixels",
}
RUNTIME_MEASUREMENT_ADAPTER_KEYS = {"name", "vendor", "api_version", "device_type", "driver_info"}
RUNTIME_MEASUREMENT_PHYSICS_KEYS = {"engine", "ticks_per_second", "max_steps_per_frame"}
RUNTIME_MEASUREMENT_MEMORY_KEYS = {
    "scope",
    "units",
    "static_bytes",
    "static_max_bytes",
    "process_rss_bytes",
    "gpu_memory_bytes",
}
RUNTIME_MEASUREMENT_PHYSICS_POINT_KEYS = {"frame_id", "timestamp_usec"}
RUNTIME_MEASUREMENT_DEFORMATION_KEYS = {"applicability", "records"}
RUNTIME_MEASUREMENT_DEFORMATION_RECORD_KEYS = {
    "sample_index",
    "operation",
    "phase",
    "logical_tick",
    "cpu_deformation_core_duration_usec",
    "evidence_inclusive_wall_duration_usec",
}
RUNTIME_DEFORMATION_APPLICABLE = "applicable"
RUNTIME_DEFORMATION_NOT_APPLICABLE = "not_applicable"
RUNTIME_DEFORMATION_UPDATE_STAGES = (
    ("contact_drive", "contact"),
    ("release_recovery", "release"),
    ("restore_baseline", "exit"),
)
RUNTIME_EVALUATION_KEYS = {"cpu_deformation", "rigid_contact_only", "capability_comparison", "paired_identities"}
RUNTIME_EVALUATION_MODE_KEYS = {
    "raw_measurement",
    "summary",
    "semantic_contact",
    "semantic_deformation",
    "semantic_render_collision_coherence",
}
RUNTIME_EVALUATION_SUMMARY_KEYS = {"targets", "physics_interval", "cpu_deformation_update"}
RUNTIME_EVALUATION_TIMING_SUMMARY_KEYS = {
    "sample_count",
    "p95_rank",
    "p95_usec",
    "maximum_usec",
    "above_screen_count",
    "screen_usec",
    "within_screen",
}
RUNTIME_EVALUATION_CAPABILITY_KEYS = {"semantic_contact", "physical_response", "deformation", "captures"}
RUNTIME_EVALUATION_COMPARISON_KEYS = {
    "cpu_deformation",
    "rigid_contact_only",
    "visual_equivalence",
}
RUNTIME_EVALUATION_PAIRED_IDENTITY_KEYS = {
    "validated_gallery",
    "validated_carrier",
    "semantic_pose_command",
    "validated_ck_projection",
    "semantic_contact_command",
    "project",
    "script",
    "launcher",
    "executable",
}


def _safe_avatar_root_name(index: int, instance_id: str) -> str:
    """Return the deterministic Godot root name used by the carrier probe."""
    return f"Avatar_{index:02d}_{instance_id.replace('-', '_')}"


def _carrier_avatar_records(carrier: dict[str, Any]) -> list[dict[str, str]]:
    """Project validated carrier instances into the minimal Godot input records."""
    records: list[dict[str, str]] = []
    for instance in carrier["instances"]:
        records.append(
            {
                "instance_id": instance["instance_id"],
                "profile_id": instance["profile_id"],
                "candidate_profile_sha256": instance["candidate_profile_sha256"],
            }
        )
    return records


def _expected_carrier_avatar_bindings(records: list[dict[str, str]]) -> list[dict[str, Any]]:
    bindings: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        metadata = {
            "ck_experiment_instance_id": record["instance_id"],
            "ck_profile_id": record["profile_id"],
            "ck_candidate_profile_sha256": record["candidate_profile_sha256"],
        }
        bindings.append(
            {
                **record,
                "root_name": _safe_avatar_root_name(index, record["instance_id"]),
                "root_metadata": metadata,
            }
        )
    return bindings


def _carrier_identity(carrier: dict[str, Any], carrier_module: Any) -> dict[str, Any]:
    canonical = carrier_module._canonical_json(carrier)
    return {
        "sha256": hashlib.sha256(canonical).hexdigest(),
        "byte_count_decimal": str(len(canonical)),
        "schema": carrier_module.SCHEMA,
        "boundary": carrier_module.BOUNDARY,
        "experiment_instance_ids": [instance["instance_id"] for instance in carrier["instances"]],
    }


def _validated_carrier_input(
    gallery: Path,
    carrier_path: Path,
) -> tuple[Any, dict[str, Any], dict[str, Any], tuple[str, str], tuple[str, str]]:
    carrier_module = _load_carrier_module()
    try:
        carrier = carrier_module.load_carrier(carrier_path)
        payload, profile_ids, instance_ids = carrier_module.validate_carrier(carrier, gallery)
    except carrier_module.CarrierError as exc:
        raise SmokeError(f"disposable avatar carrier rejected: {exc}") from exc
    identity = _carrier_identity(carrier, carrier_module)
    if tuple(identity["experiment_instance_ids"]) != instance_ids:
        raise SmokeError("disposable avatar carrier instance order is internally inconsistent")
    return carrier_module, carrier, payload, profile_ids, instance_ids


def _projection_bindings(projection: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "instance_id": avatar["instance_id"],
            "profile_id": avatar["profile_id"],
            "candidate_profile_sha256": avatar["candidate_profile_sha256"],
            "source": avatar["source"],
            "artifacts": avatar["artifacts"],
        }
        for avatar in projection["avatars"]
    ]


def _validated_projection_input(
    gallery: Path,
    carrier_path: Path,
    carrier: dict[str, Any],
    payload: dict[str, Any],
    profile_ids: tuple[str, str],
    instance_ids: tuple[str, str],
    carrier_identity: dict[str, Any],
    carrier_avatar_records: list[dict[str, str]],
    projection_path: Path,
    projection_cli_path: Path,
) -> tuple[Any, dict[str, Any], dict[str, Any]]:
    projection_module = _load_projection_module()
    try:
        projection = projection_module.validate_projection(
            projection_path,
            gallery,
            carrier_path,
            cli_path=projection_cli_path,
        )
        identity = projection_module.projection_identity(projection)
    except projection_module.ProjectionError as exc:
        raise SmokeError(f"disposable CK projection rejected: {exc}") from exc

    expected_carrier = {
        "schema": carrier_identity["schema"],
        "boundary": carrier_identity["boundary"],
        "sha256": carrier_identity["sha256"],
        "bytes": int(carrier_identity["byte_count_decimal"]),
        "instance_ids": list(instance_ids),
    }
    if projection["carrier_identity"] != expected_carrier:
        raise SmokeError("CK projection carrier identity does not match the fresh carrier")
    expected_gallery = {
        "projection_contract": carrier["source_gallery"]["projection_contract"],
        "manifest_sha256": carrier["source_gallery"]["manifest_sha256"],
        "manifest_bytes": carrier["source_gallery"]["manifest_bytes"],
        "boundary": carrier["source_gallery"]["boundary"],
        "profile_ids": list(profile_ids),
    }
    if projection["gallery_identity"] != expected_gallery:
        raise SmokeError("CK projection gallery identity does not match the fresh carrier payload")
    if projection["shared_pose"] != carrier["shared_pose"]:
        raise SmokeError("CK projection shared pose does not match the fresh carrier payload")
    avatars = projection["avatars"]
    if len(avatars) != len(carrier_avatar_records) or len(avatars) != len(payload["profiles"]):
        raise SmokeError("CK projection does not contain the exact ordered carrier profiles")
    for index, (avatar, carrier_record, carrier_instance, expected_profile) in enumerate(
        zip(avatars, carrier_avatar_records, carrier["instances"], payload["profiles"])
    ):
        if (
            avatar["instance_id"] != carrier_record["instance_id"]
            or avatar["profile_id"] != carrier_record["profile_id"]
            or avatar["candidate_profile_sha256"] != carrier_record["candidate_profile_sha256"]
            or avatar["profile_id"] != profile_ids[index]
            or avatar["label"] != carrier_instance["label"]
        ):
            raise SmokeError(f"CK projection avatar {index} identity/order disagrees with the fresh carrier")
        if avatar["candidate_profile_sha256"] != expected_profile["candidate_profile_sha256"]:
            raise SmokeError(f"CK projection avatar {index} candidate identity disagrees with the fresh payload")
        if avatar["artifacts"] != expected_profile["artifacts"] or len(avatar["artifacts"]) != 6:
            raise SmokeError(f"CK projection avatar {index} artifacts disagree with the fresh payload")
        if avatar["metrics"] != expected_profile["metrics"]:
            raise SmokeError(f"CK projection avatar {index} metrics disagree with the fresh payload")
    return projection_module, projection, identity


def _ck_package_report_identity(manifest: dict[str, Any]) -> dict[str, Any]:
    """Project a validated package into the exact conditional report record."""
    package_module = _load_package_module()
    try:
        schema = package_module.SCHEMA
        boundary = package_module.BOUNDARY
    except AttributeError as exc:
        raise SmokeError("disposable CK package module does not expose its identity") from exc
    avatars = manifest.get("avatars")
    if not isinstance(avatars, list) or len(avatars) != 2:
        raise SmokeError("validated CK package does not contain exactly two avatar records")
    records: list[dict[str, Any]] = []
    for index, avatar in enumerate(avatars):
        if not isinstance(avatar, dict):
            raise SmokeError(f"validated CK package avatar {index} is not an object")
        records.append(
            {
                "ordinal": index,
                "instance_id": avatar.get("instance_id"),
                "profile_id": avatar.get("profile_id"),
                "candidate_profile_sha256": avatar.get("candidate_profile_sha256"),
            }
        )
    return {
        "schema": schema,
        "boundary": boundary,
        "manifest_identity": deepcopy(manifest.get("manifest_identity")),
        "projection_identity": deepcopy(manifest.get("projection_identity")),
        "avatar_records": records,
    }


def _package_file_bytes(package_module: Any, package_root: Path, relative: str, label: str) -> bytes:
    try:
        carrier_module = _load_carrier_module()
        return package_module._read_regular_file(  # type: ignore[attr-defined]
            carrier_module,
            package_root / relative,
            package_module.MAX_FILE_BYTES,
            label,
        )
    except SmokeError:
        raise
    except Exception as exc:
        raise SmokeError(f"{label} could not be read from the validated CK package: {type(exc).__name__}: {exc}") from exc


def _gallery_metrics_bytes(package_module: Any, gallery: Path, profile_id: str) -> bytes:
    label = f"gallery {profile_id} metrics"
    try:
        return _load_carrier_module()._read_regular_file(  # type: ignore[attr-defined]
            Path(gallery) / profile_id / package_module.METRICS_FILE,
            package_module.MAX_FILE_BYTES,
            label,
        )
    except SmokeError:
        raise
    except Exception as exc:
        raise SmokeError(
            f"{label} could not be read during CK package validation: {type(exc).__name__}: {exc}"
        ) from exc


def _stage_validated_ck_package(
    package_path: Path,
    package_manifest: dict[str, Any],
    staging_root: Path,
) -> tuple[Path, dict[str, Any]]:
    """Copy and revalidate the exact package payload used by the Godot child."""
    package_module = _load_package_module()
    package_path = Path(package_path)
    staging_root = Path(staging_root)
    try:
        records = package_module._manifest_file_records(package_manifest)  # type: ignore[attr-defined]
        manifest_bytes = package_module._canonical_json(package_manifest)
        staging_root.mkdir(mode=0o700)
        package_module._make_layout(staging_root)  # type: ignore[attr-defined]
        for relative in sorted(records):
            data = _package_file_bytes(package_module, package_path, relative, f"package file {relative}")
            package_module._write_new_file(  # type: ignore[attr-defined]
                staging_root / relative,
                data,
                f"staged CK package file {relative}",
            )
        package_module._write_new_file(  # type: ignore[attr-defined]
            staging_root / package_module.MANIFEST_FILE,
            manifest_bytes,
            "staged CK package manifest",
        )
        staged_manifest = package_module.validate_package(staging_root)
    except SmokeError:
        raise
    except Exception as exc:
        raise SmokeError(f"CK package staging failed: {type(exc).__name__}: {exc}") from exc
    if not isinstance(staged_manifest, dict) or not _exact_json_equal(staged_manifest, package_manifest):
        raise SmokeError("staged CK package validation does not match the already validated package")
    return staging_root, staged_manifest


def _validated_ck_package_input(
    package_path: Path,
    gallery: Path,
    projection: dict[str, Any],
    projection_identity: dict[str, Any],
) -> tuple[Any, dict[str, Any], dict[str, Any]]:
    """Validate the package independently, then bind it to fresh projection evidence."""
    package_module = _load_package_module()
    package_path = Path(package_path)
    try:
        manifest = package_module.validate_package(package_path)
    except Exception as exc:
        package_error = getattr(package_module, "PackageError", ValueError)
        if isinstance(exc, package_error):
            raise SmokeError(f"disposable CK package rejected: {exc}") from exc
        raise SmokeError(f"disposable CK package validation failed: {type(exc).__name__}: {exc}") from exc
    if not isinstance(manifest, dict):
        raise SmokeError("disposable CK package validator did not return a manifest object")
    if manifest.get("projection_identity") != projection_identity:
        raise SmokeError("CK package projection identity does not match the freshly validated projection")

    package_avatars = manifest.get("avatars")
    projection_avatars = projection.get("avatars")
    if not isinstance(package_avatars, list) or not isinstance(projection_avatars, list):
        raise SmokeError("CK package and projection avatar records are not ordered arrays")
    if len(package_avatars) != 2 or len(projection_avatars) != 2:
        raise SmokeError("CK package and projection must contain exactly two ordered avatars")

    for index, (package_avatar, projection_avatar) in enumerate(zip(package_avatars, projection_avatars)):
        if not isinstance(package_avatar, dict) or not isinstance(projection_avatar, dict):
            raise SmokeError(f"CK package avatar {index} is not an object")
        for key in ("instance_id", "profile_id", "candidate_profile_sha256"):
            if package_avatar.get(key) != projection_avatar.get(key):
                raise SmokeError(f"CK package avatar {index} identity/order disagrees with the projection")
        if package_avatar.get("runtime_input_inspection") != projection_avatar.get("runtime_input_inspection"):
            raise SmokeError(f"CK package avatar {index} runtime-input evidence disagrees with the projection")

        package_source = package_avatar.get("source")
        projection_source = projection_avatar.get("source")
        if not isinstance(package_source, dict) or not isinstance(projection_source, dict):
            raise SmokeError(f"CK package avatar {index} source identity is incomplete")
        for key in ("sha256", "bytes", "document", "namespace"):
            if package_source.get(key) != projection_source.get(key):
                raise SmokeError(f"CK package avatar {index} source identity disagrees with the projection")

        package_artifacts = package_avatar.get("artifacts")
        projection_artifacts = projection_avatar.get("artifacts")
        if not isinstance(package_artifacts, list) or not isinstance(projection_artifacts, list):
            raise SmokeError(f"CK package avatar {index} artifact records are incomplete")
        if len(package_artifacts) != 6 or len(projection_artifacts) != 6:
            raise SmokeError(f"CK package avatar {index} must contain exactly six ordered artifacts")
        for artifact_index, (package_artifact, projection_artifact) in enumerate(
            zip(package_artifacts, projection_artifacts)
        ):
            if not isinstance(package_artifact, dict) or not isinstance(projection_artifact, dict):
                raise SmokeError(f"CK package avatar {index} artifact {artifact_index} is incomplete")
            for key in ("sha256", "bytes"):
                if package_artifact.get(key) != projection_artifact.get(key):
                    raise SmokeError(
                        f"CK package avatar {index} artifact {artifact_index} hash or byte count disagrees with the projection"
                    )

        package_metrics = package_avatar.get("metrics")
        if not isinstance(package_metrics, dict):
            raise SmokeError(f"CK package avatar {index} metrics file identity is incomplete")
        profile_id = package_avatar.get("profile_id")
        if not isinstance(profile_id, str):
            raise SmokeError(f"CK package avatar {index} profile identity is invalid")
        package_metrics_bytes = _package_file_bytes(
            package_module,
            package_path,
            str(package_metrics.get("path", "")),
            f"CK package {profile_id} metrics",
        )
        try:
            metrics_value = package_module._parse_json_bytes(  # type: ignore[attr-defined]
                package_metrics_bytes,
                f"CK package {profile_id} metrics",
            )
        except Exception as exc:
            raise SmokeError(f"CK package {profile_id} metrics are not valid JSON: {exc}") from exc
        if metrics_value != projection_avatar.get("metrics"):
            raise SmokeError(f"CK package avatar {index} metrics disagree with the projection")
        expected_metrics_bytes = _gallery_metrics_bytes(package_module, gallery, profile_id)
        if package_metrics_bytes != expected_metrics_bytes:
            raise SmokeError(f"CK package avatar {index} metrics file differs from the freshly validated gallery")

    return package_module, manifest, _ck_package_report_identity(manifest)


def _validated_semantic_pose_command(
    gallery: Path,
    carrier_path: Path,
    carrier: dict[str, Any],
    payload: dict[str, Any],
    profile_ids: tuple[str, str],
    instance_ids: tuple[str, str],
    command_path: Path,
) -> tuple[Any, dict[str, Any], dict[str, Any], dict[str, Any]]:
    command_module = _load_command_module()
    try:
        command = command_module.load_command(command_path)
        command_module.validate_command(command, gallery, carrier_path)
        command_identity = command_module.command_identity(command)
        semantic_payload = command_module.semantic_payload(command)
    except command_module.CommandError as exc:
        raise SmokeError(f"disposable semantic pose command rejected: {exc}") from exc
    expected_targets = _carrier_avatar_records(carrier)
    if command.get("targets") != expected_targets:
        raise SmokeError("semantic pose command targets do not match the validated carrier")
    if command.get("source_pose", {}).get("pose_id") != payload["pose_id"] or command.get("source_pose", {}).get("sha256") != payload["pose_sha256"]:
        raise SmokeError("semantic pose command source identity does not match the validated gallery")
    if tuple(target["instance_id"] for target in command["targets"]) != instance_ids or tuple(target["profile_id"] for target in command["targets"]) != profile_ids:
        raise SmokeError("semantic pose command target order is inconsistent with the validated carrier")
    return command_module, command, command_identity, semantic_payload


def _exact_json_equal(left: Any, right: Any) -> bool:
    """Compare JSON-shaped values without Python's bool/int equivalence."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return set(left) == set(right) and all(_exact_json_equal(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(_exact_json_equal(a, b) for a, b in zip(left, right))
    return left == right


def _validate_contact_command_contract(
    contact_command: Any,
    carrier: dict[str, Any],
    pose_command_identity: dict[str, Any],
) -> None:
    """Enforce the fixed experiment-only contact command contract locally."""
    if not isinstance(contact_command, dict):
        raise SmokeError("disposable semantic contact command is not a JSON object")
    expected_keys = {
        "schema",
        "boundary",
        "command_id",
        "command_version",
        "mapping_revision",
        "targets",
        "source_pose_command",
        "participants",
        "interaction",
    }
    if set(contact_command) != expected_keys:
        raise SmokeError("semantic contact command has unexpected or missing fields")
    if (
        contact_command["schema"] != CONTACT_COMMAND_SCHEMA
        or contact_command["boundary"] != CONTACT_COMMAND_BOUNDARY
        or contact_command["command_id"] != CONTACT_COMMAND_ID
        or type(contact_command["command_version"]) is not int
        or contact_command["command_version"] != CONTACT_COMMAND_VERSION
        or contact_command["mapping_revision"] != CONTACT_MAPPING_REVISION
    ):
        raise SmokeError("semantic contact command schema, boundary, or identity is invalid")
    expected_targets = _carrier_avatar_records(carrier)
    if not _exact_json_equal(contact_command["targets"], expected_targets):
        raise SmokeError("semantic contact command targets do not match the validated carrier")
    if not _exact_json_equal(contact_command["source_pose_command"], pose_command_identity):
        raise SmokeError("semantic contact command source pose identity does not match the semantic pose command")
    if not _exact_json_equal(contact_command["participants"], CONTACT_PARTICIPANTS):
        raise SmokeError("semantic contact command participants are not the exact ordered actuator/response pair")
    if not _exact_json_equal(contact_command["interaction"], CONTACT_INTERACTION):
        raise SmokeError("semantic contact command interaction is not the fixed press-release sequence")


def _validated_semantic_contact_command(
    gallery: Path,
    carrier_path: Path,
    carrier: dict[str, Any],
    pose_command_path: Path,
    pose_command: dict[str, Any],
    pose_command_identity: dict[str, Any],
    contact_command_path: Path,
) -> tuple[Any, dict[str, Any], dict[str, Any]]:
    """Load and freshly validate one contact command against all predecessors."""
    contact_module = _load_contact_command_module()
    try:
        contact_command = contact_module.load_contact_command(contact_command_path)
        contact_module.validate_contact_command(
            contact_command,
            gallery,
            carrier_path,
            pose_command_path,
        )
        _validate_contact_command_contract(contact_command, carrier, pose_command_identity)
        contact_identity = contact_module.command_identity(contact_command)
    except SmokeError:
        raise
    except Exception as exc:
        contact_error = getattr(contact_module, "ContactCommandError", ValueError)
        if isinstance(exc, contact_error):
            raise SmokeError(f"disposable semantic contact command rejected: {exc}") from exc
        raise SmokeError(f"disposable semantic contact command validation failed: {exc}") from exc
    if not isinstance(contact_identity, dict):
        raise SmokeError("disposable semantic contact command identity is invalid")
    return contact_module, contact_command, contact_identity


def _finite_number(value: Any) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(float(value))
    except OverflowError:
        return False


def _validate_finite_report_json(value: Any, where: str = "Godot report") -> None:
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, (int, float)):
        if not _finite_number(value):
            raise SmokeError(f"{where} contains non-finite or unbounded numeric evidence")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_finite_report_json(item, f"{where}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _validate_finite_report_json(item, f"{where}.{key}")
        return
    raise SmokeError(f"{where} contains a non-JSON value")


def _require_exact_fields(value: Any, expected: set[str], where: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise SmokeError(f"{where} has unexpected or missing fields")


def _validate_runtime_measurement_mode(mode: Any) -> str:
    if mode not in RUNTIME_MEASUREMENT_MODES:
        raise SmokeError(
            "runtime measurement mode must be exactly one of: "
            + ", ".join(RUNTIME_MEASUREMENT_MODES)
        )
    return str(mode)


def _validate_runtime_string(value: Any, where: str, *, allow_empty: bool = False) -> None:
    if not isinstance(value, str) or (not allow_empty and not value):
        qualifier = " or empty" if allow_empty else ""
        raise SmokeError(f"{where} must be a string{qualifier}")


def _validate_runtime_nonnegative(value: Any, where: str, *, integer: bool = False) -> None:
    if integer:
        if type(value) is not int:
            raise SmokeError(f"{where} must be a nonnegative integer")
    elif not _finite_number(value):
        raise SmokeError(f"{where} must be a finite nonnegative number")
    numeric = int(value) if integer else float(value)
    if numeric < 0:
        raise SmokeError(f"{where} must be a finite nonnegative number")


def _runtime_contact_update_ticks(contact_report: dict[str, Any]) -> list[int]:
    evidence = contact_report.get("semantic_contact")
    if not isinstance(evidence, dict):
        raise SmokeError("runtime measurement requires semantic contact evidence")
    tick_evidence = evidence.get("contact_tick_evidence")
    if not isinstance(tick_evidence, list):
        raise SmokeError("runtime measurement cannot derive deformation update ticks")
    ticks: list[int] = []
    for record in tick_evidence:
        if not isinstance(record, dict):
            raise SmokeError("runtime measurement contact tick evidence is malformed")
        if record.get("phase") == "contact" and type(record.get("contact_count")) is int and record["contact_count"] > 0:
            if type(record.get("tick")) is not int:
                raise SmokeError("runtime measurement contact tick evidence has an invalid tick")
            ticks.append(record["tick"])
    if not ticks:
        raise SmokeError("runtime measurement requires at least one contact-driven deformation update tick")
    return ticks


def _validate_runtime_measurement(
    value: Any,
    expected_mode: str,
    contact_report: dict[str, Any],
    *,
    include_runner_release: bool = False,
) -> None:
    expected_mode = _validate_runtime_measurement_mode(expected_mode)
    expected_keys = RUNTIME_MEASUREMENT_FINAL_KEYS if include_runner_release else RUNTIME_MEASUREMENT_KEYS
    _require_exact_fields(value, expected_keys, "Godot runtime_measurement")
    if value["schema"] != RUNTIME_MEASUREMENT_SCHEMA or value["boundary"] != RUNTIME_MEASUREMENT_BOUNDARY:
        raise SmokeError("Godot runtime_measurement schema or boundary is invalid")
    if value["mode"] != expected_mode:
        raise SmokeError("Godot runtime_measurement mode does not match the requested launch mode")

    for key, expected in (
        ("godot", RUNTIME_MEASUREMENT_GODOT_KEYS),
        ("os", RUNTIME_MEASUREMENT_OS_KEYS),
        ("cpu", RUNTIME_MEASUREMENT_CPU_KEYS),
        ("renderer", RUNTIME_MEASUREMENT_RENDERER_KEYS),
        ("adapter", RUNTIME_MEASUREMENT_ADAPTER_KEYS),
        ("physics", RUNTIME_MEASUREMENT_PHYSICS_KEYS),
        ("memory", RUNTIME_MEASUREMENT_MEMORY_KEYS),
    ):
        _require_exact_fields(value.get(key), expected, f"Godot runtime_measurement.{key}")

    _validate_runtime_string(value["godot"]["version"], "Godot runtime_measurement.godot.version")
    _validate_runtime_string(
        value["godot"]["engine_version_string"],
        "Godot runtime_measurement.godot.engine_version_string",
    )
    if value["godot"]["version"] != EXPECTED_GODOT_VERSION:
        raise SmokeError("Godot runtime_measurement Godot version is not exact")
    if value["godot"]["engine_version_string"] != EXPECTED_GODOT_ENGINE_VERSION_STRING:
        raise SmokeError("Godot runtime_measurement engine version string is not exact")
    for key in ("name", "distribution_name", "version", "architecture"):
        _validate_runtime_string(value["os"][key], f"Godot runtime_measurement.os.{key}")
    _validate_runtime_string(value["os"]["model_name"], "Godot runtime_measurement.os.model_name", allow_empty=True)
    _validate_runtime_string(value["cpu"]["processor_name"], "Godot runtime_measurement.cpu.processor_name")
    _validate_runtime_nonnegative(
        value["cpu"]["processor_count"],
        "Godot runtime_measurement.cpu.processor_count",
        integer=True,
    )
    if value["cpu"]["processor_count"] == 0:
        raise SmokeError("Godot runtime_measurement.cpu.processor_count must be positive")
    _validate_runtime_string(value["renderer"]["method"], "Godot runtime_measurement.renderer.method")
    if value["renderer"]["method"] != "gl_compatibility":
        raise SmokeError("Godot runtime_measurement renderer method is not the launched renderer")
    _validate_runtime_string(value["renderer"]["driver_name"], "Godot runtime_measurement.renderer.driver_name")
    if value["renderer"]["requested_display_driver"] != "x11":
        raise SmokeError("Godot runtime_measurement requested display driver is not x11")
    if value["renderer"]["actual_display_server"] != "X11":
        raise SmokeError("Godot runtime_measurement actual display server is not X11")
    if value["renderer"]["window_size_pixels"] != [512, 512]:
        raise SmokeError("Godot runtime_measurement effective window size is not 512x512")
    for key in ("name", "vendor", "api_version"):
        _validate_runtime_string(value["adapter"][key], f"Godot runtime_measurement.adapter.{key}")
    _validate_runtime_nonnegative(value["adapter"]["device_type"], "Godot runtime_measurement.adapter.device_type", integer=True)
    if not isinstance(value["adapter"]["driver_info"], list) or any(
        not isinstance(item, str) for item in value["adapter"]["driver_info"]
    ):
        raise SmokeError("Godot runtime_measurement.adapter.driver_info must be an array of strings")
    _validate_runtime_string(value["physics"]["engine"], "Godot runtime_measurement.physics.engine")
    if value["physics"]["engine"] != "Jolt Physics":
        raise SmokeError("Godot runtime_measurement physics engine is not the required Jolt Physics backend")
    _validate_runtime_nonnegative(
        value["physics"]["ticks_per_second"],
        "Godot runtime_measurement.physics.ticks_per_second",
        integer=True,
    )
    if value["physics"]["ticks_per_second"] != RUNTIME_MEASUREMENT_TARGETS["physics_hz"]:
        raise SmokeError("Godot runtime_measurement physics tick rate does not match the trial target")
    _validate_runtime_nonnegative(
        value["physics"]["max_steps_per_frame"],
        "Godot runtime_measurement.physics.max_steps_per_frame",
        integer=True,
    )
    if value["physics"]["max_steps_per_frame"] <= 0:
        raise SmokeError("Godot runtime_measurement.physics.max_steps_per_frame must be positive")
    if (
        value["memory"]["scope"] != "godot_allocator_snapshot_not_process_rss_or_gpu_memory"
        or value["memory"]["units"] != "bytes"
        or value["memory"]["process_rss_bytes"] is not None
        or value["memory"]["gpu_memory_bytes"] is not None
    ):
        raise SmokeError("Godot runtime_measurement memory scope is invalid or overclaims unavailable measurements")
    for key in ("static_bytes", "static_max_bytes"):
        _validate_runtime_nonnegative(value["memory"][key], f"Godot runtime_measurement.memory.{key}")

    timestamp_points = value["physics_timestamp_points"]
    if not isinstance(timestamp_points, list) or len(timestamp_points) != RUNTIME_MEASUREMENT_PHYSICS_SAMPLE_COUNT + 1:
        raise SmokeError("Godot runtime_measurement must contain exactly 65 physics timestamp/frame-id points")
    timestamps: list[int] = []
    for expected_frame_id, point in enumerate(timestamp_points):
        _require_exact_fields(point, RUNTIME_MEASUREMENT_PHYSICS_POINT_KEYS, "Godot runtime physics timestamp point")
        if type(point["frame_id"]) is not int or point["frame_id"] != expected_frame_id:
            raise SmokeError("Godot runtime physics timestamp frame IDs are missing, reordered, or duplicated")
        _validate_runtime_nonnegative(point["timestamp_usec"], "Godot runtime physics timestamp", integer=True)
        timestamps.append(point["timestamp_usec"])
    interval_values = [right - left for left, right in zip(timestamps, timestamps[1:])]
    if len(interval_values) != RUNTIME_MEASUREMENT_PHYSICS_SAMPLE_COUNT or any(value <= 0 for value in interval_values):
        raise SmokeError("Godot runtime physics timestamps must define exactly 64 positive consecutive intervals")

    deformation_updates = value["cpu_deformation_updates"]
    _require_exact_fields(deformation_updates, RUNTIME_MEASUREMENT_DEFORMATION_KEYS, "Godot runtime deformation updates")
    applicability = deformation_updates["applicability"]
    if applicability not in (RUNTIME_DEFORMATION_APPLICABLE, RUNTIME_DEFORMATION_NOT_APPLICABLE):
        raise SmokeError("Godot runtime deformation update applicability is invalid")
    update_samples = deformation_updates["records"]
    if not isinstance(update_samples, list):
        raise SmokeError("Godot runtime deformation update records are not an array")
    contact_update_ticks = _runtime_contact_update_ticks(contact_report)
    if expected_mode == "rigid_contact_only":
        if applicability != RUNTIME_DEFORMATION_NOT_APPLICABLE or update_samples:
            raise SmokeError("rigid_contact_only runtime measurement must explicitly declare deformation not_applicable")
    elif applicability != RUNTIME_DEFORMATION_APPLICABLE:
        raise SmokeError("cpu_deformation runtime measurement must declare deformation applicable")
    expected_update_stages = [
        ("contact_drive", "contact", tick) for tick in contact_update_ticks
    ]
    release_start = CONTACT_PHASE_TICKS[0] + CONTACT_PHASE_TICKS[1] + 1
    release_end = release_start + CONTACT_PHASE_TICKS[2]
    restore_start = release_end
    restore_end = restore_start + CONTACT_PHASE_TICKS[3]
    expected_update_stages.extend(
        ("release_recovery", "release", tick) for tick in range(release_start, release_end)
    )
    expected_update_stages.extend(
        ("restore_baseline", "exit", tick) for tick in range(restore_start, restore_end)
    )
    if expected_mode == "cpu_deformation" and len(update_samples) != len(expected_update_stages):
        raise SmokeError(
            "cpu_deformation runtime measurement does not contain one duration for every contact, release, and restore update"
        )
    for expected_index, (sample, (expected_operation, expected_phase, expected_tick)) in enumerate(
        zip(update_samples, expected_update_stages)
    ):
        _require_exact_fields(
            sample,
            RUNTIME_MEASUREMENT_DEFORMATION_RECORD_KEYS,
            "Godot runtime deformation update sample",
        )
        if type(sample["sample_index"]) is not int or sample["sample_index"] != expected_index:
            raise SmokeError("Godot runtime deformation update samples are missing, reordered, or duplicated")
        if sample["operation"] != expected_operation or sample["phase"] != expected_phase:
            raise SmokeError("Godot runtime deformation update operation or phase is not the exact applicable update")
        if type(sample["logical_tick"]) is not int or sample["logical_tick"] != expected_tick:
            raise SmokeError("Godot runtime deformation update sample tick is not the exact applicable update tick")
        _validate_runtime_nonnegative(
            sample["cpu_deformation_core_duration_usec"],
            "Godot runtime deformation CPU deformation-core duration",
            integer=True,
        )
        _validate_runtime_nonnegative(
            sample["evidence_inclusive_wall_duration_usec"],
            "Godot runtime deformation evidence-inclusive wall duration",
            integer=True,
        )
        if sample["evidence_inclusive_wall_duration_usec"] < sample["cpu_deformation_core_duration_usec"]:
            raise SmokeError(
                "Godot runtime deformation evidence-inclusive wall duration cannot be less than the CPU deformation-core duration"
            )

    if include_runner_release:
        _validate_runtime_string(value["runner_os_uname_release"], "Python runner os.uname().release")


def _nearest_rank_p95(values: list[int]) -> int:
    if not values:
        raise SmokeError("cannot calculate p95 for an empty runtime measurement sample set")
    rank = max(1, math.ceil(0.95 * len(values)))
    return sorted(values)[rank - 1]


def _runtime_measurement_with_runner_release(value: dict[str, Any]) -> dict[str, Any]:
    measurement = deepcopy(value)
    try:
        release = os.uname().release
    except AttributeError as exc:
        raise SmokeError("Python runner cannot observe os.uname().release") from exc
    if not isinstance(release, str) or not release:
        raise SmokeError("Python runner os.uname().release is empty or invalid")
    measurement["runner_os_uname_release"] = release
    return measurement


def _runtime_file_identity(path: Path, label: str) -> dict[str, str]:
    if path.is_symlink() or not path.is_file():
        raise SmokeError(f"runtime evaluation {label} identity source is unavailable: {path}")
    digest = hashlib.sha256()
    byte_count = 0
    try:
        with path.open("rb") as source:
            while chunk := source.read(1024 * 1024):
                digest.update(chunk)
                byte_count += len(chunk)
    except OSError as exc:
        raise SmokeError(f"runtime evaluation {label} identity source cannot be read: {type(exc).__name__}: {exc}") from exc
    return {"sha256": digest.hexdigest(), "byte_count_decimal": str(byte_count)}


def _runtime_launch_identity() -> dict[str, dict[str, str]]:
    try:
        pinned_binary = neutral_smoke._resolve_pinned_binary()
    except SmokeError:
        raise
    except Exception as exc:
        raise SmokeError(f"runtime evaluation pinned executable identity could not be resolved: {exc}") from exc
    return {
        "project": _runtime_file_identity(neutral_smoke.PROJECT_FILE, "project"),
        "script": _runtime_file_identity(GODOT_SCRIPT, "script"),
        "launcher": _runtime_file_identity(neutral_smoke.LAUNCHER, "launcher"),
        "executable": _runtime_file_identity(pinned_binary, "executable"),
    }


def _runtime_paired_identities(
    cpu_report: dict[str, Any],
    rigid_report: dict[str, Any],
    launch_identity: dict[str, dict[str, str]],
) -> dict[str, Any]:
    report_identity_keys = (
        "validated_gallery",
        "validated_carrier",
        "semantic_pose_command_identity",
        "validated_ck_projection",
    )
    for key in report_identity_keys:
        cpu_identity = cpu_report.get(key)
        rigid_identity = rigid_report.get(key)
        if not isinstance(cpu_identity, dict) or not isinstance(rigid_identity, dict):
            raise SmokeError(f"runtime evaluation paired reports are missing stable {key} identity")
        _validate_finite_report_json(cpu_identity, f"runtime evaluation {key} identity")
        _validate_finite_report_json(rigid_identity, f"runtime evaluation {key} identity")
        if cpu_identity != rigid_identity:
            raise SmokeError(f"runtime evaluation paired reports disagree on stable {key} identity")
    cpu_package = cpu_report.get("validated_ck_package")
    rigid_package = rigid_report.get("validated_ck_package")
    if (cpu_package is None) != (rigid_package is None):
        raise SmokeError("runtime evaluation paired reports disagree on CK package identity presence")
    if cpu_package is not None:
        _validate_ck_package_report_identity(cpu_package, cpu_package, True)
        _validate_ck_package_report_identity(rigid_package, cpu_package, True)
    cpu_contact = cpu_report.get("semantic_contact")
    rigid_contact = rigid_report.get("semantic_contact")
    if not isinstance(cpu_contact, dict) or not isinstance(rigid_contact, dict):
        raise SmokeError("runtime evaluation paired reports are missing stable semantic contact identity")
    cpu_contact_identity = cpu_contact.get("command_identity")
    rigid_contact_identity = rigid_contact.get("command_identity")
    if not isinstance(cpu_contact_identity, dict) or not isinstance(rigid_contact_identity, dict):
        raise SmokeError("runtime evaluation paired reports are missing semantic contact command identity")
    _validate_finite_report_json(cpu_contact_identity, "runtime evaluation semantic contact identity")
    _validate_finite_report_json(rigid_contact_identity, "runtime evaluation semantic contact identity")
    if cpu_contact_identity != rigid_contact_identity:
        raise SmokeError("runtime evaluation paired reports disagree on stable semantic contact identity")
    _require_exact_fields(
        launch_identity,
        {"project", "script", "launcher", "executable"},
        "runtime evaluation launch identity",
    )
    for key in ("project", "script", "launcher", "executable"):
        _require_exact_fields(launch_identity[key], {"sha256", "byte_count_decimal"}, f"runtime evaluation {key} identity")
        _validate_runtime_string(launch_identity[key]["sha256"], f"runtime evaluation {key} SHA-256")
        if len(launch_identity[key]["sha256"]) != 64:
            raise SmokeError(f"runtime evaluation {key} SHA-256 identity is invalid")
        _validate_runtime_string(launch_identity[key]["byte_count_decimal"], f"runtime evaluation {key} byte count")
        if not launch_identity[key]["byte_count_decimal"].isdigit() or int(launch_identity[key]["byte_count_decimal"]) <= 0:
            raise SmokeError(f"runtime evaluation {key} byte count identity is invalid")
    paired = {
        "validated_gallery": deepcopy(cpu_report["validated_gallery"]),
        "validated_carrier": deepcopy(cpu_report["validated_carrier"]),
        "semantic_pose_command": deepcopy(cpu_report["semantic_pose_command_identity"]),
        "validated_ck_projection": deepcopy(cpu_report["validated_ck_projection"]),
        "semantic_contact_command": deepcopy(cpu_contact_identity),
        **deepcopy(launch_identity),
    }
    if cpu_package is not None:
        paired["validated_ck_package"] = deepcopy(cpu_package)
    return paired


def _runtime_measurement_summary(measurement: dict[str, Any]) -> dict[str, Any]:
    timestamps = [point["timestamp_usec"] for point in measurement["physics_timestamp_points"]]
    interval_values = [right - left for left, right in zip(timestamps, timestamps[1:])]
    update_values = [
        sample["cpu_deformation_core_duration_usec"]
        for sample in measurement["cpu_deformation_updates"]["records"]
    ]
    interval_p95 = _nearest_rank_p95(interval_values)
    update_p95 = _nearest_rank_p95(update_values) if update_values else None
    return {
        "targets": deepcopy(RUNTIME_MEASUREMENT_TARGETS),
        "physics_interval": {
            "sample_count": len(interval_values),
            "p95_rank": math.ceil(0.95 * len(interval_values)),
            "p95_usec": interval_p95,
            "maximum_usec": max(interval_values),
            "above_screen_count": sum(
                value > RUNTIME_MEASUREMENT_TARGETS["p95_physics_interval_screen_usec"]
                for value in interval_values
            ),
            "screen_usec": RUNTIME_MEASUREMENT_TARGETS["p95_physics_interval_screen_usec"],
            "within_screen": interval_p95 <= RUNTIME_MEASUREMENT_TARGETS["p95_physics_interval_screen_usec"],
        },
        "cpu_deformation_update": {
            "sample_count": len(update_values),
            "p95_rank": math.ceil(0.95 * len(update_values)) if update_values else None,
            "p95_usec": update_p95,
            "maximum_usec": max(update_values) if update_values else None,
            "above_screen_count": (
                sum(value > RUNTIME_MEASUREMENT_TARGETS["p95_cpu_deformation_update_screen_usec"] for value in update_values)
                if update_values
                else None
            ),
            "screen_usec": RUNTIME_MEASUREMENT_TARGETS["p95_cpu_deformation_update_screen_usec"],
            "within_screen": (
                update_p95 <= RUNTIME_MEASUREMENT_TARGETS["p95_cpu_deformation_update_screen_usec"]
                if update_p95 is not None
                else None
            ),
        },
    }


def _validate_runtime_summary(summary: Any, measurement: dict[str, Any]) -> None:
    _require_exact_fields(summary, RUNTIME_EVALUATION_SUMMARY_KEYS, "runtime evaluation summary")
    if summary["targets"] != RUNTIME_MEASUREMENT_TARGETS:
        raise SmokeError("runtime evaluation target declarations are invalid")
    timestamps = [point["timestamp_usec"] for point in measurement["physics_timestamp_points"]]
    interval_values = [right - left for left, right in zip(timestamps, timestamps[1:])]
    update_values = [
        sample["cpu_deformation_core_duration_usec"]
        for sample in measurement["cpu_deformation_updates"]["records"]
    ]
    for key, values in (("physics_interval", interval_values), ("cpu_deformation_update", update_values)):
        _require_exact_fields(summary[key], RUNTIME_EVALUATION_TIMING_SUMMARY_KEYS, f"runtime evaluation {key} summary")
        expected_p95 = _nearest_rank_p95(values) if values else None
        expected = {
            "sample_count": len(values),
            "p95_rank": math.ceil(0.95 * len(values)) if values else None,
            "p95_usec": expected_p95,
            "maximum_usec": max(values) if values else None,
            "above_screen_count": (
                sum(
                    value
                    > (
                        RUNTIME_MEASUREMENT_TARGETS["p95_physics_interval_screen_usec"]
                        if key == "physics_interval"
                        else RUNTIME_MEASUREMENT_TARGETS["p95_cpu_deformation_update_screen_usec"]
                    )
                    for value in values
                )
                if values
                else None
            ),
            "screen_usec": (
                RUNTIME_MEASUREMENT_TARGETS["p95_physics_interval_screen_usec"]
                if key == "physics_interval"
                else RUNTIME_MEASUREMENT_TARGETS["p95_cpu_deformation_update_screen_usec"]
            ),
            "within_screen": (
                expected_p95 <= (
                    RUNTIME_MEASUREMENT_TARGETS["p95_physics_interval_screen_usec"]
                    if key == "physics_interval"
                    else RUNTIME_MEASUREMENT_TARGETS["p95_cpu_deformation_update_screen_usec"]
                )
                if expected_p95 is not None
                else None
            ),
        }
        if summary[key] != expected:
            raise SmokeError(f"runtime evaluation {key} summary is not independently derived from raw samples")


def _runtime_child_evidence(report: dict[str, Any], mode: str) -> dict[str, Any]:
    if not isinstance(report, dict):
        raise SmokeError(f"runtime evaluation {mode} child report is not an object")
    semantic_contact = report.get("semantic_contact")
    if not isinstance(semantic_contact, dict):
        raise SmokeError(f"runtime evaluation {mode} child semantic contact evidence is missing")
    if mode == "cpu_deformation":
        for key in ("semantic_deformation", "semantic_render_collision_coherence"):
            if not isinstance(report.get(key), dict):
                raise SmokeError(f"runtime evaluation {mode} child {key} evidence is missing")
    elif any(key in report for key in ("semantic_deformation", "semantic_render_collision_coherence")):
        raise SmokeError(f"runtime evaluation {mode} child contains unexpected deformation evidence")
    return {
        "semantic_contact": deepcopy(semantic_contact),
        "semantic_deformation": deepcopy(report.get("semantic_deformation")) if mode == "cpu_deformation" else None,
        "semantic_render_collision_coherence": (
            deepcopy(report.get("semantic_render_collision_coherence")) if mode == "cpu_deformation" else None
        ),
    }


def _runtime_evidence_capabilities(evidence: dict[str, Any]) -> dict[str, bool]:
    semantic_contact = evidence["semantic_contact"]
    semantic_deformation = evidence["semantic_deformation"]
    return {
        "semantic_contact": isinstance(semantic_contact, dict),
        "physical_response": (
            isinstance(semantic_contact, dict)
            and isinstance(semantic_contact.get("response"), dict)
            and isinstance(semantic_contact.get("solver_impulses"), list)
        ),
        "deformation": isinstance(semantic_deformation, dict),
        "captures": (
            isinstance(semantic_deformation, dict)
            and isinstance(semantic_deformation.get("captures"), list)
        ),
    }


def _validate_runtime_evaluation(
    value: Any,
    cpu_report: dict[str, Any],
    rigid_report: dict[str, Any],
    expected_paired_identities: dict[str, Any] | None = None,
    *,
    semantic_contact_command: dict[str, Any] | None = None,
    contact_command_identity: dict[str, Any] | None = None,
) -> None:
    _require_exact_fields(value, RUNTIME_EVALUATION_KEYS, "runtime_evaluation")
    measurements: dict[str, dict[str, Any]] = {}
    child_reports = {
        "cpu_deformation": cpu_report,
        "rigid_contact_only": rigid_report,
    }
    child_evidence: dict[str, dict[str, Any]] = {}
    for mode in RUNTIME_MEASUREMENT_MODES:
        _require_exact_fields(value[mode], RUNTIME_EVALUATION_MODE_KEYS, f"runtime_evaluation.{mode}")
        raw = value[mode]["raw_measurement"]
        _validate_runtime_measurement(raw, mode, child_reports[mode], include_runner_release=True)
        _validate_runtime_summary(value[mode]["summary"], raw)
        expected_evidence = _runtime_child_evidence(child_reports[mode], mode)
        actual_evidence = {
            key: value[mode][key]
            for key in (
                "semantic_contact",
                "semantic_deformation",
                "semantic_render_collision_coherence",
            )
        }
        if actual_evidence != expected_evidence:
            raise SmokeError(
                f"runtime evaluation {mode} semantic evidence does not match its independently validated child report"
            )
        if semantic_contact_command is not None or contact_command_identity is not None:
            if semantic_contact_command is None or contact_command_identity is None:
                raise SmokeError("runtime evaluation semantic contact validation requires command and identity")
            evidence_report = dict(child_reports[mode])
            evidence_report.update(actual_evidence)
            strongest_sample = _validate_contact_report(
                evidence_report,
                semantic_contact_command,
                contact_command_identity,
            )
            if mode == "cpu_deformation":
                _validate_deformation_report(evidence_report, strongest_sample)
                _validate_render_collision_coherence(evidence_report, strongest_sample)
        child_evidence[mode] = actual_evidence
        measurements[mode] = raw
    shared_keys = ("schema", "boundary", "godot", "os", "cpu", "renderer", "adapter", "physics", "runner_os_uname_release")
    for key in shared_keys:
        if measurements["cpu_deformation"][key] != measurements["rigid_contact_only"][key]:
            raise SmokeError(f"runtime evaluation paired measurements disagree on shared {key} metadata")
    comparison = value["capability_comparison"]
    _require_exact_fields(comparison, RUNTIME_EVALUATION_COMPARISON_KEYS, "runtime evaluation capability comparison")
    for mode in RUNTIME_MEASUREMENT_MODES:
        _require_exact_fields(comparison[mode], RUNTIME_EVALUATION_CAPABILITY_KEYS, f"runtime evaluation {mode} capabilities")
        if any(type(comparison[mode][key]) is not bool for key in RUNTIME_EVALUATION_CAPABILITY_KEYS):
            raise SmokeError(f"runtime evaluation {mode} capabilities are not exact booleans")
        if comparison[mode] != _runtime_evidence_capabilities(child_evidence[mode]):
            raise SmokeError(f"runtime evaluation {mode} capabilities are not derived from evidence")
    if comparison["visual_equivalence"] != "not_claimed":
        raise SmokeError("runtime evaluation capability comparison is invalid")
    paired_identities = value["paired_identities"]
    paired_identity_keys = set(RUNTIME_EVALUATION_PAIRED_IDENTITY_KEYS)
    has_package_identity = "validated_ck_package" in paired_identities if isinstance(paired_identities, dict) else False
    if has_package_identity:
        paired_identity_keys.add("validated_ck_package")
    _require_exact_fields(paired_identities, paired_identity_keys, "runtime evaluation paired identities")
    for key in (
        "validated_gallery",
        "validated_carrier",
        "semantic_pose_command",
        "validated_ck_projection",
        "semantic_contact_command",
    ):
        if not isinstance(paired_identities[key], dict):
            raise SmokeError(f"runtime evaluation paired {key} identity is missing")
        _validate_finite_report_json(paired_identities[key], f"runtime evaluation paired {key} identity")
    if has_package_identity:
        if not isinstance(paired_identities["validated_ck_package"], dict):
            raise SmokeError("runtime evaluation paired validated CK package identity is missing")
        _validate_ck_package_report_identity(
            paired_identities["validated_ck_package"],
            paired_identities["validated_ck_package"],
            True,
        )
    for key in ("project", "script", "launcher", "executable"):
        _require_exact_fields(
            paired_identities[key],
            {"sha256", "byte_count_decimal"},
            f"runtime evaluation paired {key} identity",
        )
        _validate_runtime_string(paired_identities[key]["sha256"], f"runtime evaluation paired {key} SHA-256")
        if len(paired_identities[key]["sha256"]) != 64:
            raise SmokeError(f"runtime evaluation paired {key} SHA-256 identity is invalid")
        _validate_runtime_string(
            paired_identities[key]["byte_count_decimal"],
            f"runtime evaluation paired {key} byte count",
        )
        if not paired_identities[key]["byte_count_decimal"].isdigit() or int(paired_identities[key]["byte_count_decimal"]) <= 0:
            raise SmokeError(f"runtime evaluation paired {key} byte count identity is invalid")
    if expected_paired_identities is not None and paired_identities != expected_paired_identities:
        raise SmokeError("runtime evaluation paired identities do not match the independently validated child reports")


def _build_runtime_evaluation(
    cpu_report: dict[str, Any],
    rigid_report: dict[str, Any],
    paired_identities: dict[str, Any],
    semantic_contact_command: dict[str, Any],
    contact_command_identity: dict[str, Any],
) -> dict[str, Any]:
    cpu_measurement = _runtime_measurement_with_runner_release(cpu_report["runtime_measurement"])
    rigid_measurement = _runtime_measurement_with_runner_release(rigid_report["runtime_measurement"])
    _validate_runtime_measurement(
        cpu_measurement,
        "cpu_deformation",
        cpu_report,
        include_runner_release=True,
    )
    _validate_runtime_measurement(
        rigid_measurement,
        "rigid_contact_only",
        rigid_report,
        include_runner_release=True,
    )
    runtime_evaluation = {
        "cpu_deformation": {
            "raw_measurement": cpu_measurement,
            "summary": _runtime_measurement_summary(cpu_measurement),
            **_runtime_child_evidence(cpu_report, "cpu_deformation"),
        },
        "rigid_contact_only": {
            "raw_measurement": rigid_measurement,
            "summary": _runtime_measurement_summary(rigid_measurement),
            **_runtime_child_evidence(rigid_report, "rigid_contact_only"),
        },
        "capability_comparison": {
            "cpu_deformation": _runtime_evidence_capabilities(
                _runtime_child_evidence(cpu_report, "cpu_deformation")
            ),
            "rigid_contact_only": _runtime_evidence_capabilities(
                _runtime_child_evidence(rigid_report, "rigid_contact_only")
            ),
            "visual_equivalence": "not_claimed",
        },
        "paired_identities": deepcopy(paired_identities),
    }
    _validate_runtime_evaluation(
        runtime_evaluation,
        cpu_report,
        rigid_report,
        paired_identities,
        semantic_contact_command=semantic_contact_command,
        contact_command_identity=contact_command_identity,
    )
    return runtime_evaluation


def _expected_gallery_identity(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "projection_contract": payload["projection_contract"],
        "manifest_sha256": payload["manifest_sha256"],
        "manifest_bytes": payload["manifest_bytes"],
        "pose_id": payload["pose_id"],
        "pose_sha256": payload["pose_sha256"],
        "boundary": payload["boundary"],
    }


def _expected_artifact_identities(payload: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    return {profile["profile_id"]: profile["artifacts"] for profile in payload["profiles"]}


def _require_exact_bool(value: Any, where: str) -> None:
    if type(value) is not bool:
        raise SmokeError(f"{where} must be an exact boolean")


def _require_finite_metric(value: Any, where: str) -> None:
    if not _finite_number(value):
        raise SmokeError(f"{where} must be a finite number")


def _validate_binding(binding: Any, profile_id: str) -> None:
    if not isinstance(binding, dict):
        raise SmokeError(f"Godot report profile {profile_id} binding evidence is incomplete")
    exact = {
        "skeleton_bone_count": BONE_COUNT,
        "skin_bind_count": BONE_COUNT,
        "unique_bone_names": True,
        "parent_links_match": True,
        "neutral_rest_matches_published": True,
        "skin_bind_poses_match_published": True,
        "mesh_skeleton_path_bound": True,
        "mesh_skin_bound": True,
        "neutral_baked_mesh_matches": True,
        "posed_baked_mesh_matches": True,
        "pose_rules_applied": BONE_COUNT,
        "pose_global_matrices_match": BONE_COUNT,
        "skin_matrices_match": BONE_COUNT,
        "posed_proxy_nodes_match": PROXY_COUNT,
        "tolerance": TOLERANCE,
        "normal_tolerance": NORMAL_TOLERANCE,
    }
    for key, expected in exact.items():
        if key not in binding:
            raise SmokeError(f"Godot report profile {profile_id} binding.{key} is missing")
        actual = binding[key]
        if isinstance(expected, bool):
            _require_exact_bool(actual, f"Godot report profile {profile_id} binding.{key}")
        if actual != expected:
            raise SmokeError(f"Godot report profile {profile_id} binding.{key} is invalid")
    for key in (
        "max_neutral_vertex_error",
        "max_neutral_normal_error",
        "max_posed_vertex_error",
        "max_posed_normal_error",
        "max_posed_proxy_endpoint_error",
    ):
        if key not in binding:
            raise SmokeError(f"Godot report profile {profile_id} binding.{key} is missing")
        _require_finite_metric(binding[key], f"Godot report profile {profile_id} binding.{key}")
        if float(binding[key]) < 0.0:
            raise SmokeError(f"Godot report profile {profile_id} {key} must be non-negative")
        limit = NORMAL_TOLERANCE if "normal" in key else TOLERANCE
        if float(binding[key]) > limit:
            raise SmokeError(f"Godot report profile {profile_id} {key} exceeds tolerance")


def _validate_carrier_report_identity(
    actual: Any,
    expected: dict[str, Any] | None,
    present: bool,
) -> None:
    if expected is None:
        if present:
            raise SmokeError("legacy Godot report contains unexpected validated-carrier evidence")
        return
    keys = {"sha256", "byte_count_decimal", "schema", "boundary", "experiment_instance_ids"}
    if not isinstance(actual, dict) or set(actual) != keys:
        raise SmokeError("Godot report validated-carrier identity is incomplete")
    if (
        not isinstance(actual["sha256"], str)
        or len(actual["sha256"]) != 64
        or not isinstance(actual["byte_count_decimal"], str)
        or not actual["byte_count_decimal"].isascii()
        or not actual["byte_count_decimal"].isdigit()
        or actual["byte_count_decimal"].startswith("0")
        or len(actual["byte_count_decimal"]) > 7
        or int(actual["byte_count_decimal"]) > 4 * 1024 * 1024
        or not isinstance(actual["schema"], str)
        or not isinstance(actual["boundary"], str)
        or not isinstance(actual["experiment_instance_ids"], list)
        or len(actual["experiment_instance_ids"]) != 2
        or any(not isinstance(value, str) for value in actual["experiment_instance_ids"])
        or actual["experiment_instance_ids"][0] == actual["experiment_instance_ids"][1]
        or actual != expected
    ):
        raise SmokeError("Godot report validated-carrier identity is invalid")


def _validate_ck_package_report_identity(
    actual: Any,
    expected: dict[str, Any] | None,
    present: bool,
) -> None:
    if expected is None:
        if present:
            raise SmokeError("non-package Godot report contains unexpected validated CK package evidence")
        return
    if not present or not isinstance(actual, dict):
        raise SmokeError("Godot report validated_ck_package record is missing")
    if set(actual) != {
        "schema",
        "boundary",
        "manifest_identity",
        "projection_identity",
        "avatar_records",
    }:
        raise SmokeError("Godot report validated_ck_package record has unexpected or missing fields")
    avatar_records = actual.get("avatar_records")
    if not isinstance(avatar_records, list) or len(avatar_records) != 2:
        raise SmokeError("Godot report validated_ck_package avatar_records are incomplete or reordered")
    for index, record in enumerate(avatar_records):
        if not isinstance(record, dict) or set(record) != {
            "ordinal",
            "instance_id",
            "profile_id",
            "candidate_profile_sha256",
        }:
            raise SmokeError(f"Godot report validated_ck_package avatar record {index} is incomplete")
        if type(record.get("ordinal")) is not int or record["ordinal"] != index:
            raise SmokeError("Godot report validated_ck_package avatar records are reordered")
    if actual != expected:
        raise SmokeError("Godot report validated_ck_package record does not match the validated package")


def _validate_carrier_avatar_bindings(
    actual: Any,
    expected_records: list[dict[str, str]] | None,
    present: bool,
) -> None:
    if expected_records is None:
        if present:
            raise SmokeError("no-carrier Godot report contains unexpected avatar binding evidence")
        return
    if not present:
        raise SmokeError("Godot report is aggregate-only; carrier avatar binding read-back is missing")
    expected = _expected_carrier_avatar_bindings(expected_records)
    if not isinstance(actual, list) or len(actual) != len(expected):
        raise SmokeError("Godot report carrier avatar bindings are incomplete or reordered")
    for index, (observed, expected_binding) in enumerate(zip(actual, expected)):
        if not isinstance(observed, dict) or set(observed) != set(expected_binding):
            raise SmokeError(f"Godot report carrier avatar binding {index} is incomplete")
        metadata = observed.get("root_metadata")
        expected_metadata = expected_binding["root_metadata"]
        if not isinstance(metadata, dict) or set(metadata) != set(expected_metadata):
            raise SmokeError(f"Godot report carrier avatar binding {index} metadata is incomplete")
        if observed != expected_binding:
            raise SmokeError(
                "Godot report carrier avatar bindings are missing, duplicate, reordered, swapped, or mismatched"
            )


def _validate_carrier_expectations(
    carrier_identity: dict[str, Any] | None,
    carrier_avatar_records: list[dict[str, str]] | None,
    payload: dict[str, Any],
    profile_ids: tuple[str, str],
) -> None:
    if (carrier_identity is None) != (carrier_avatar_records is None):
        raise SmokeError("carrier identity and per-avatar expectations must be supplied together")
    if carrier_identity is None or carrier_avatar_records is None:
        return
    keys = {"instance_id", "profile_id", "candidate_profile_sha256"}
    if (
        len(carrier_avatar_records) != 2
        or any(not isinstance(record, dict) or set(record) != keys for record in carrier_avatar_records)
    ):
        raise SmokeError("carrier per-avatar expectations are incomplete")
    instance_ids = [record["instance_id"] for record in carrier_avatar_records]
    expected_hashes = [profile["candidate_profile_sha256"] for profile in payload["profiles"]]
    if (
        carrier_identity.get("experiment_instance_ids") != instance_ids
        or [record["profile_id"] for record in carrier_avatar_records] != list(profile_ids)
        or [record["candidate_profile_sha256"] for record in carrier_avatar_records] != expected_hashes
    ):
        raise SmokeError("carrier identity, profile order, and per-avatar expectations are inconsistent")


def _validate_command_expectations(
    actual_identity: Any,
    actual_targets: Any,
    actual_frame: Any,
    command: dict[str, Any] | None,
    command_identity: dict[str, Any] | None,
    payload: dict[str, Any],
    carrier_avatar_records: list[dict[str, str]] | None,
) -> None:
    report_fields_present = (actual_identity is not None, actual_targets is not None, actual_frame is not None)
    if command is None:
        if any(report_fields_present):
            raise SmokeError("no-command Godot report contains unexpected semantic pose command evidence")
        return
    if command_identity is None or carrier_avatar_records is None:
        raise SmokeError("semantic pose command requires carrier and command identity expectations")
    command_module = _load_command_module()
    try:
        command_module._validate_shape(command)
        expected_identity = command_module.command_identity(command)
        expected_frame = command["identity_frame"]
    except command_module.CommandError as exc:
        raise SmokeError(f"semantic pose command expectation is invalid: {exc}") from exc
    if command_identity != expected_identity:
        raise SmokeError("semantic pose command identity is inconsistent")
    if command["source_pose"] != {
        "format": "creature-kernel.disposable-structural-embodiment-shared-pose.v1",
        "pose_id": payload["pose_id"],
        "sha256": payload["pose_sha256"],
        "version": 1,
    }:
        raise SmokeError("semantic pose command source identity is inconsistent")
    if command["targets"] != carrier_avatar_records:
        raise SmokeError("semantic pose command targets are not bound to the carrier records")
    if actual_identity != expected_identity or actual_targets != command["targets"] or actual_frame != expected_frame:
        raise SmokeError("Godot report semantic pose command identity, targets, or frame evidence is invalid")


def _validate_command_injection(
    actual: Any,
    target: dict[str, str],
    command: dict[str, Any],
    profile_id: str,
) -> None:
    keys = {
        "target",
        "rule_readback",
        "rules_observed",
        "local_pose_matches_command",
        "global_pose_matches_published",
        "skin_matrices_match_published",
        "applied",
    }
    if not isinstance(actual, dict) or set(actual) != keys or actual.get("target") != target:
        raise SmokeError(f"Godot report profile {profile_id} semantic pose injection evidence is incomplete")
    for key in (
        "rules_observed",
        "local_pose_matches_command",
        "global_pose_matches_published",
        "skin_matrices_match_published",
    ):
        if type(actual.get(key)) is not int or actual[key] != BONE_COUNT:
            raise SmokeError(f"Godot report profile {profile_id} semantic pose injection {key} is invalid")
    if type(actual.get("applied")) is not bool or actual["applied"] is not True:
        raise SmokeError(f"Godot report profile {profile_id} semantic pose injection applied flag is invalid")
    readback = actual.get("rule_readback")
    if not isinstance(readback, list) or len(readback) != BONE_COUNT:
        raise SmokeError(f"Godot report profile {profile_id} semantic pose rule read-back is incomplete")
    runtime_bone_ids: set[str] = set()
    for index, (record, rule) in enumerate(zip(readback, command["rules"])):
        expected_selector = _command_selector(rule)
        if not isinstance(record, dict) or set(record) != {
            "selector",
            "runtime_bone_id",
            "observed_rotation_xyzw",
            "max_component_error_to_command",
        }:
            raise SmokeError(f"Godot report profile {profile_id} semantic pose rule {index} is incomplete")
        runtime_bone_id = record["runtime_bone_id"]
        if (
            record["selector"] != expected_selector
            or type(runtime_bone_id) is not str
            or not runtime_bone_id
            or runtime_bone_id in runtime_bone_ids
        ):
            raise SmokeError(f"Godot report profile {profile_id} semantic pose rule {index} routing is invalid")
        runtime_bone_ids.add(runtime_bone_id)
        observed = record["observed_rotation_xyzw"]
        if not isinstance(observed, list) or len(observed) != 4 or any(not _finite_number(value) for value in observed):
            raise SmokeError(f"Godot report profile {profile_id} semantic pose rule {index} rotation is invalid")
        expected = rule["rotation_xyzw"]
        direct_error = max(abs(float(left) - float(right)) for left, right in zip(observed, expected))
        antipodal_error = max(abs(float(left) + float(right)) for left, right in zip(observed, expected))
        observed_error = min(direct_error, antipodal_error)
        reported_error = record["max_component_error_to_command"]
        if (
            not _finite_number(reported_error)
            or float(reported_error) < 0.0
            or float(reported_error) > SEMANTIC_POSE_QUATERNION_TOLERANCE
            or observed_error > SEMANTIC_POSE_QUATERNION_TOLERANCE
            or abs(float(reported_error) - observed_error) > SEMANTIC_POSE_QUATERNION_TOLERANCE
        ):
            raise SmokeError(f"Godot report profile {profile_id} semantic pose rule {index} does not match the command")


def _command_selector(rule: dict[str, Any]) -> str:
    role = "" if rule["role"] is None else rule["role"]
    return f"{rule['kind']}|{role}|{','.join(rule['anchors'])}"


def _contact_vector(value: Any, where: str) -> list[float]:
    if not isinstance(value, list) or len(value) != 3 or any(not _finite_number(item) for item in value):
        raise SmokeError(f"{where} must be a finite three-vector")
    return [float(item) for item in value]


def _contact_scalar(value: Any, where: str) -> float:
    if not _finite_number(value):
        raise SmokeError(f"{where} must be a finite number")
    return float(value)


def _contact_snapshot_position(value: Any, where: str) -> list[float]:
    if not isinstance(value, list) or len(value) != 16 or any(not _finite_number(item) for item in value):
        raise SmokeError(f"{where} is not finite runtime transform evidence")
    homogeneous_row = [float(item) for item in value[12:16]]
    if homogeneous_row != [0.0, 0.0, 0.0, 1.0]:
        raise SmokeError(f"{where} is not a homogeneous runtime transform")
    basis = [float(value[index]) for index in (0, 1, 2, 4, 5, 6, 8, 9, 10)]
    if basis != [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]:
        raise SmokeError(f"{where} does not have the required identity basis")
    return [float(value[3]), float(value[7]), float(value[11])]


def _validate_contact_snapshot(value: Any, label: str, where: str) -> dict[str, Any]:
    required = {"label", "tick", "transform", "position", "linear_velocity", "angular_velocity"}
    if not isinstance(value, dict) or set(value) != required:
        raise SmokeError(f"{where} is incomplete or aliased")
    if value["label"] != label:
        raise SmokeError(f"{where} label is invalid")
    if type(value["tick"]) is not int or value["tick"] < 0 or value["tick"] > CONTACT_TOTAL_TICKS:
        raise SmokeError(f"{where} tick is invalid")
    transform_position = _contact_snapshot_position(value["transform"], f"{where}.transform")
    position = _contact_vector(value["position"], f"{where}.position")
    if any(abs(transform - reported) > TOLERANCE for transform, reported in zip(transform_position, position)):
        raise SmokeError(f"{where} transform and position disagree")
    return {
        "tick": value["tick"],
        "position": position,
        "linear_velocity": _contact_vector(value["linear_velocity"], f"{where}.linear_velocity"),
        "angular_velocity": _contact_vector(value["angular_velocity"], f"{where}.angular_velocity"),
    }


def _contact_compare_scalar(reported: Any, expected: float, where: str) -> float:
    value = _contact_scalar(reported, where)
    if abs(value - expected) > TOLERANCE:
        raise SmokeError(f"{where} does not match the emitted snapshots")
    return value


def _contact_evidence_from_report(report: dict[str, Any]) -> dict[str, Any]:
    if "semantic_contact" not in report:
        raise SmokeError("Godot report is missing semantic contact evidence")
    if CONTACT_REPORT_ALIAS_KEYS.intersection(report):
        raise SmokeError("Godot report contains unsupported semantic contact aliases")
    evidence = report["semantic_contact"]
    if not isinstance(evidence, dict):
        raise SmokeError("Godot semantic contact evidence is not an object")
    return evidence


def _validate_contact_mapping(
    evidence: dict[str, Any],
    contact_command: dict[str, Any],
) -> None:
    participants = evidence["participants"]
    if not isinstance(participants, list) or len(participants) != len(CONTACT_PARTICIPANTS):
        raise SmokeError("semantic contact participant mapping is incomplete or aggregate-only")
    mappings = evidence["selector_mappings"]
    if not isinstance(mappings, list) or len(mappings) != len(CONTACT_PARTICIPANTS):
        raise SmokeError("semantic contact selector-to-proxy mapping is incomplete or aggregate-only")
    if not _exact_json_equal(contact_command["participants"], CONTACT_PARTICIPANTS):
        raise SmokeError("semantic contact command participants are not the fixed ordered pair")

    seen_selectors: set[str] = set()
    seen_bones: set[str] = set()
    seen_proxies: set[str] = set()
    seen_shapes: set[tuple[int, int]] = set()
    seen_owned: set[str] = set()
    for index, expected in enumerate(CONTACT_PARTICIPANTS):
        participant = participants[index]
        if not isinstance(participant, dict) or set(participant) != {
            "role",
            "target_index",
            "target",
            "selector",
            "source_joint",
            "source_bone_id",
            "source_proxy_index",
            "posed_proxy",
            "runtime_shape_index",
        }:
            raise SmokeError(f"semantic contact participant {index} is incomplete or aliased")
        if (
            type(participant.get("target_index")) is not int
            or participant.get("target_index") != expected["target_index"]
            or participant.get("role") != expected["role"]
            or not _exact_json_equal(participant.get("selector"), expected["selector"])
            or not _exact_json_equal(participant.get("target"), contact_command["targets"][index])
            or not _exact_json_equal(participant.get("source_joint"), CONTACT_SOURCE_JOINTS[index])
            or participant.get("source_bone_id") != CONTACT_BONE_IDS[index]
            or type(participant.get("source_bone_id")) is not str
            or type(participant.get("source_proxy_index")) is not int
            or participant.get("source_proxy_index") != CONTACT_SHAPE_INDICES[index]
            or type(participant.get("runtime_shape_index")) is not int
            or participant.get("runtime_shape_index") != CONTACT_RUNTIME_SHAPE_INDICES[index]
        ):
            raise SmokeError("semantic contact participant roles, selectors, or order are invalid")
        selector_key = json.dumps(expected["selector"], sort_keys=True, separators=(",", ":"))
        if selector_key in seen_selectors:
            raise SmokeError("semantic contact selector mapping contains a duplicate selector")
        seen_selectors.add(selector_key)

        posed_proxy = participant["posed_proxy"]
        if not isinstance(posed_proxy, dict) or set(posed_proxy) != {
            "a",
            "b",
            "bone_id",
            "kind",
            "owned_part",
            "partition_rule",
            "partition_vertex_count",
            "radius",
            "radius_rule",
        }:
            raise SmokeError("semantic contact posed-proxy lineage is incomplete or aliased")
        if (
            posed_proxy["kind"] != "capsule"
            or posed_proxy["bone_id"] != CONTACT_BONE_IDS[index]
            or not _exact_json_equal(posed_proxy["owned_part"], CONTACT_OWNED_PARTS[index])
            or posed_proxy["partition_rule"] != CONTACT_PROXY_PARTITION_RULE
            or type(posed_proxy["partition_vertex_count"]) is not int
            or posed_proxy["partition_vertex_count"] <= 0
            or posed_proxy["radius_rule"] != CONTACT_PROXY_RADIUS_RULE
        ):
            raise SmokeError("semantic contact posed-proxy lineage is not exact")
        _contact_vector(posed_proxy["a"], f"semantic contact mapping {index}.posed_proxy.a")
        _contact_vector(posed_proxy["b"], f"semantic contact mapping {index}.posed_proxy.b")
        radius = _contact_scalar(posed_proxy["radius"], f"semantic contact mapping {index}.posed_proxy.radius")
        if radius <= 0.0:
            raise SmokeError("semantic contact posed-proxy radius is not positive")

        mapping_value = mappings[index]
        mapping = mapping_value
        if not isinstance(mapping, dict) or set(mapping) != {
            "role",
            "target_index",
            "selector",
            "bone_id",
            "proxy_id",
            "owned_part",
            "shape_index",
            "runtime_shape_index",
        }:
            raise SmokeError(f"semantic contact selector mapping {index} is incomplete or aliased")
        if (
            type(mapping.get("target_index")) is not int
            or mapping.get("target_index") != expected["target_index"]
            or mapping.get("role") != expected["role"]
            or not _exact_json_equal(mapping.get("selector"), expected["selector"])
            or mapping.get("bone_id") != participant["source_bone_id"]
            or mapping.get("proxy_id") != participant["source_bone_id"]
            or not _exact_json_equal(mapping.get("owned_part"), posed_proxy["owned_part"])
            or mapping.get("shape_index") != participant["source_proxy_index"]
            or mapping.get("runtime_shape_index") != participant["runtime_shape_index"]
        ):
            raise SmokeError("semantic contact selector mappings are missing, reordered, or swapped")
        bone_id = mapping["bone_id"]
        proxy_id = mapping["proxy_id"]
        owned_part = mapping["owned_part"]
        shape_index = mapping["shape_index"]
        runtime_shape_index = mapping["runtime_shape_index"]
        if type(bone_id) is not str or type(proxy_id) is not str:
            raise SmokeError("semantic contact selector-to-bone mapping is not exact")
        if bone_id != CONTACT_BONE_IDS[index] or proxy_id != CONTACT_BONE_IDS[index]:
            raise SmokeError("semantic contact selector-to-proxy mapping is not exact")
        if not _exact_json_equal(owned_part, CONTACT_OWNED_PARTS[index]):
            raise SmokeError("semantic contact owned_part mapping is not exact")
        if type(shape_index) is not int or shape_index != CONTACT_SHAPE_INDICES[index]:
            raise SmokeError("semantic contact actuator/response shape indices are invalid")
        if type(runtime_shape_index) is not int or runtime_shape_index != CONTACT_RUNTIME_SHAPE_INDICES[index]:
            raise SmokeError("semantic contact runtime shape indices are invalid")
        shape_key = (expected["target_index"], shape_index)
        owned_key = json.dumps(owned_part, sort_keys=True, separators=(",", ":"))
        if (
            bone_id in seen_bones
            or proxy_id in seen_proxies
            or shape_key in seen_shapes
            or owned_key in seen_owned
        ):
            raise SmokeError("semantic contact selector mapping contains duplicate runtime evidence")
        seen_bones.add(bone_id)
        seen_proxies.add(proxy_id)
        seen_shapes.add(shape_key)
        seen_owned.add(owned_key)


def _validate_contact_ticks(evidence: dict[str, Any]) -> dict[int, dict[str, Any]]:
    phase_order = evidence["phase_order"]
    if not _exact_json_equal(phase_order, CONTACT_PHASE_ORDER):
        raise SmokeError("semantic contact phase order is missing, reordered, or invalid")
    max_ticks = evidence["max_ticks"]
    if type(max_ticks) is not int or max_ticks != CONTACT_MAX_TICKS:
        raise SmokeError("semantic contact tick bound is not the declared bounded budget")
    phase_ticks = evidence["phase_ticks"]
    expected_start = 1
    values = []
    if not isinstance(phase_ticks, list) or len(phase_ticks) != len(CONTACT_PHASE_ORDER):
        raise SmokeError("semantic contact phase tick schedule is incomplete or reordered")
    for index, (record, phase, expected_ticks) in enumerate(zip(phase_ticks, CONTACT_PHASE_ORDER, CONTACT_PHASE_TICKS)):
        expected_end = expected_start + expected_ticks - 1
        if (
            not isinstance(record, dict)
            or set(record) != {"phase", "ticks", "start_tick", "end_tick"}
            or record["phase"] != phase
            or type(record["ticks"]) is not int
            or record["ticks"] != expected_ticks
            or type(record["start_tick"]) is not int
            or record["start_tick"] != expected_start
            or type(record["end_tick"]) is not int
            or record["end_tick"] != expected_end
        ):
            raise SmokeError(f"semantic contact phase tick schedule {index} is missing, reordered, or invalid")
        values.append(record["ticks"])
        expected_start = expected_end + 1
    if any(type(value) is not int or value <= 0 or value > CONTACT_MAX_TICKS for value in values):
        raise SmokeError("semantic contact phase ticks are outside the bounded range")
    if sum(values) > max_ticks:
        raise SmokeError("semantic contact phase ticks exceed the declared bound")

    tick_evidence = evidence["contact_tick_evidence"]
    if not isinstance(tick_evidence, list) or len(tick_evidence) != CONTACT_TOTAL_TICKS + 1:
        raise SmokeError("semantic contact tick evidence is incomplete or aggregate-only")
    trace_by_tick: dict[int, dict[str, Any]] = {}
    enter_ticks: list[int] = []
    contact_ticks: list[int] = []
    exit_ticks: list[int] = []
    previous_count = 0
    for expected_tick, record in enumerate(tick_evidence):
        if not isinstance(record, dict) or set(record) != {"tick", "phase", "contact_count"}:
            raise SmokeError("semantic contact tick evidence is malformed")
        if type(record["tick"]) is not int or record["tick"] != expected_tick:
            raise SmokeError("semantic contact tick evidence is missing, duplicated, or reordered")
        trace_by_tick[expected_tick] = record
        count = record["contact_count"]
        if type(count) is not int or count < 0:
            raise SmokeError("semantic contact tick contact count is invalid")
        if expected_tick == 0:
            if record["phase"] != "setup" or count != 0:
                raise SmokeError("semantic contact setup tick evidence is invalid")
        else:
            phase_index = next(
                (
                    index
                    for index in range(len(CONTACT_PHASE_TICKS))
                    if expected_tick <= sum(CONTACT_PHASE_TICKS[: index + 1])
                ),
                -1,
            )
            if phase_index < 0 or record["phase"] != CONTACT_PHASE_ORDER[phase_index]:
                raise SmokeError("semantic contact tick evidence phase order is invalid")
            if previous_count == 0 and count > 0:
                enter_ticks.append(expected_tick)
            if record["phase"] == "contact" and count > 0:
                contact_ticks.append(expected_tick)
            if previous_count > 0 and count == 0:
                exit_ticks.append(expected_tick)
        previous_count = count
    if tick_evidence[-1]["phase"] != "exit" or tick_evidence[-1]["contact_count"] != 0:
        raise SmokeError("semantic contact final exit tick is not contact-free")
    if not any(
        enter_tick <= contact_tick < exit_tick
        for enter_tick in enter_ticks
        for contact_tick in contact_ticks
        for exit_tick in exit_ticks
    ):
        raise SmokeError("semantic contact enter/contact/exit phases are not proven by the tick trace")
    return trace_by_tick


def _validate_contact_impulses(
    evidence: dict[str, Any],
    trace_by_tick: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    def validate_samples(samples: Any, where: str) -> tuple[dict[str, Any], float]:
        if not isinstance(samples, list) or not samples:
            raise SmokeError(f"{where} are missing or aggregate-only")
        collider_ids: set[int] = set()
        sample_keys: set[tuple[int, int]] = set()
        previous_key: tuple[int, int] | None = None
        saw_nonzero = False
        strongest_sample: dict[str, Any] | None = None
        strongest_impulse = 0.0
        required = {
            "contact_index",
            "collider_id",
            "collider_object_id",
            "collider_shape_index",
            "local_shape_index",
            "point",
            "normal",
            "impulse",
            "tick",
            "phase",
        }
        for index, sample in enumerate(samples):
            if not isinstance(sample, dict) or set(sample) != required:
                raise SmokeError(f"{where} {index} is incomplete or echoed-only")
            for key in (
                "contact_index",
                "collider_id",
                "collider_object_id",
                "collider_shape_index",
                "local_shape_index",
                "tick",
            ):
                if type(sample[key]) is not int:
                    raise SmokeError(f"{where} {index}.{key} is invalid")
            contact_index = sample["contact_index"]
            tick = sample["tick"]
            sample_key = (tick, contact_index)
            trace = trace_by_tick.get(tick)
            if (
                tick < 0
                or tick > CONTACT_TOTAL_TICKS
                or trace is None
                or type(trace["contact_count"]) is not int
                or trace["contact_count"] <= 0
                or sample["phase"] != trace["phase"]
                or contact_index < 0
                or contact_index >= trace["contact_count"]
                or sample["collider_id"] <= 0
                or sample["collider_object_id"] <= 0
            ):
                raise SmokeError(f"{where} {index} identity is invalid")
            if sample_key in sample_keys or (previous_key is not None and sample_key <= previous_key):
                raise SmokeError(f"{where} is missing, duplicated, or reordered")
            sample_keys.add(sample_key)
            previous_key = sample_key
            if trace["phase"] not in ("contact", "release"):
                raise SmokeError(f"{where} {index} occurred outside contact/release")
            if sample["collider_shape_index"] != CONTACT_RUNTIME_SHAPE_INDICES[0] or sample["local_shape_index"] != CONTACT_RUNTIME_SHAPE_INDICES[1]:
                raise SmokeError(f"{where} shape attribution is swapped or invalid")
            _contact_vector(sample["point"], f"{where} {index}.point")
            normal = _contact_vector(sample["normal"], f"{where} {index}.normal")
            impulse_vector = _contact_vector(sample["impulse"], f"{where} {index}.impulse")
            if math.sqrt(sum(value * value for value in normal)) <= 1.0e-12:
                raise SmokeError(f"{where} {index} normal is zero")
            impulse_length = math.sqrt(sum(value * value for value in impulse_vector))
            if trace["phase"] == "contact" and impulse_length > 0.0:
                saw_nonzero = True
                if strongest_sample is None or impulse_length > strongest_impulse:
                    strongest_sample = sample
                    strongest_impulse = impulse_length
            collider_ids.add(sample["collider_id"])
            if sample["collider_object_id"] != sample["collider_id"]:
                raise SmokeError(f"{where} collider identity is mismatched")
        if len(collider_ids) != 1 or not saw_nonzero or strongest_sample is None:
            raise SmokeError(f"{where} do not prove one selected-shape pair")
        return strongest_sample, strongest_impulse

    impulses = evidence["solver_impulses"]
    if not isinstance(impulses, list) or len(impulses) != 1:
        raise SmokeError("semantic contact solver impulse evidence is missing or aggregate-only")
    record = impulses[0]
    if not isinstance(record, dict) or set(record) != {
        "runtime_derived",
        "target_indices",
        "shape_indices",
        "impulse_magnitude",
        "contact_samples",
    }:
        raise SmokeError("semantic contact solver impulse evidence is incomplete or aliased")
    if (
        type(record["runtime_derived"]) is not bool
        or not record["runtime_derived"]
        or not _exact_json_equal(record["target_indices"], [0, 1])
        or not _exact_json_equal(record["shape_indices"], list(CONTACT_SHAPE_INDICES))
    ):
        raise SmokeError("semantic contact solver impulse is not attributed to the two selected shapes")
    strongest_sample, strongest_impulse = validate_samples(record["contact_samples"], "semantic contact solver sample")
    impulse = _contact_compare_scalar(record["impulse_magnitude"], strongest_impulse, "semantic contact solver impulse")
    if impulse <= CONTACT_MIN_SOLVER_IMPULSE:
        raise SmokeError("semantic contact solver impulse is zero or below the declared floor")
    return strongest_sample


def _validate_contact_response(
    evidence: dict[str, Any],
    strongest_sample: dict[str, Any],
    trace_by_tick: dict[int, dict[str, Any]],
) -> None:
    response = evidence["response"]
    if not isinstance(response, dict) or set(response) != {
        "target_index",
        "shape_index",
        "normal",
        "snapshots",
        "normal_velocity_delta",
        "normal_displacement",
        "displacement",
    }:
        raise SmokeError("semantic contact response evidence is incomplete or aliased")
    if type(response["target_index"]) is not int or response["target_index"] != 1:
        raise SmokeError("semantic contact response body identity is invalid")
    if type(response["shape_index"]) is not int or response["shape_index"] != CONTACT_SHAPE_INDICES[1]:
        raise SmokeError("semantic contact response shape identity is invalid")

    sample_normal = _contact_vector(strongest_sample["normal"], "semantic contact strongest sample normal")
    sample_normal_length = math.sqrt(sum(value * value for value in sample_normal))
    if not math.isfinite(sample_normal_length) or sample_normal_length <= 1.0e-12:
        raise SmokeError("semantic contact strongest sample normal is zero or nonfinite")
    expected_normal = [value / sample_normal_length for value in sample_normal]
    normal = _contact_vector(response["normal"], "semantic contact normal")
    if any(abs(reported - expected) > NORMAL_TOLERANCE for reported, expected in zip(normal, expected_normal)):
        raise SmokeError("semantic contact normal does not match the strongest runtime sample")

    snapshots = response["snapshots"]
    if not isinstance(snapshots, dict) or set(snapshots) != {"initial", "onset", "contact", "final"}:
        raise SmokeError("semantic contact response snapshots are incomplete or aliased")
    initial = _validate_contact_snapshot(snapshots["initial"], "initial", "semantic contact response initial")
    onset = _validate_contact_snapshot(snapshots["onset"], "onset", "semantic contact response onset")
    contact = _validate_contact_snapshot(snapshots["contact"], "contact", "semantic contact response contact")
    final = _validate_contact_snapshot(snapshots["final"], "final", "semantic contact response final")

    initial_trace = trace_by_tick.get(initial["tick"])
    if initial["tick"] != 0 or initial_trace is None or initial_trace["phase"] != "setup" or initial_trace["contact_count"] != 0:
        raise SmokeError("semantic contact initial snapshot does not match setup tick evidence")
    first_positive_sample = _render_first_positive_contact_sample(evidence)
    onset_trace = trace_by_tick.get(onset["tick"])
    if (
        onset["tick"] <= 0
        or onset["tick"] != first_positive_sample["tick"]
        or onset_trace is None
        or onset_trace["phase"] != "contact"
        or onset_trace["contact_count"] <= 0
    ):
        raise SmokeError("semantic contact onset snapshot does not match the first validated positive contact tick")
    contact_trace = trace_by_tick.get(contact["tick"])
    if (
        contact_trace is None
        or contact["tick"] <= 0
        or contact["tick"] != strongest_sample["tick"]
        or contact_trace["phase"] != "contact"
        or contact_trace["contact_count"] <= 0
    ):
        raise SmokeError("semantic contact contact snapshot does not match the strongest positive contact tick")
    final_trace = trace_by_tick.get(final["tick"])
    if (
        final["tick"] != CONTACT_TOTAL_TICKS
        or final_trace is None
        or final_trace["phase"] != "exit"
        or final_trace["contact_count"] != 0
    ):
        raise SmokeError("semantic contact final snapshot does not match the final exit tick evidence")

    if math.sqrt(sum(value * value for value in initial["linear_velocity"])) > TOLERANCE:
        raise SmokeError("semantic contact response did not begin at rest")
    for label, snapshot in (("initial", initial), ("onset", onset), ("contact", contact), ("final", final)):
        if math.sqrt(sum(value * value for value in snapshot["angular_velocity"])) > TOLERANCE:
            raise SmokeError(f"semantic contact response {label} snapshot violates locked rotation")

    initial_position = initial["position"]
    final_position = final["position"]
    displacement = [final - initial for final, initial in zip(final_position, initial_position)]
    velocity_delta = [
        contact - initial
        for contact, initial in zip(contact["linear_velocity"], initial["linear_velocity"])
    ]
    expected_normal_velocity = abs(
        sum(value * normal_component for value, normal_component in zip(velocity_delta, expected_normal))
    )
    expected_normal_displacement = abs(sum(value * normal_component for value, normal_component in zip(displacement, expected_normal)))
    expected_displacement = math.sqrt(sum(value * value for value in displacement))
    if not all(
        math.isfinite(value)
        for value in (expected_normal_velocity, expected_normal_displacement, expected_displacement)
    ):
        raise SmokeError("semantic contact response snapshots are non-finite")
    if expected_normal_velocity <= CONTACT_MIN_NORMAL_VELOCITY_CHANGE:
        raise SmokeError("semantic contact normal velocity change is below the declared floor")
    if expected_normal_displacement <= CONTACT_MIN_RESPONSE_DISPLACEMENT:
        raise SmokeError("semantic contact response displacement is below the declared floor")
    if expected_displacement <= CONTACT_MIN_RESPONSE_DISPLACEMENT:
        raise SmokeError("semantic contact response displacement is below the declared floor")
    _contact_compare_scalar(
        response["normal_velocity_delta"], expected_normal_velocity, "semantic contact normal velocity delta"
    )
    _contact_compare_scalar(
        response["normal_displacement"], expected_normal_displacement, "semantic contact normal displacement"
    )
    _contact_compare_scalar(response["displacement"], expected_displacement, "semantic contact response displacement")


def _validate_contact_physics(evidence: dict[str, Any]) -> None:
    physics = evidence["physics_configuration"]
    if not isinstance(physics, dict) or set(physics) != {
        "physics_engine",
        "actuator_body",
        "actuator_sync_to_physics",
        "response_body",
        "response_mass",
        "response_gravity_scale",
        "response_can_sleep",
        "response_rotation_locked",
        "response_contact_monitor",
        "response_max_contacts_reported",
        "one_shape_per_contact_body",
    }:
        raise SmokeError("semantic contact physics configuration evidence is missing")
    if (
        physics["physics_engine"] != "Jolt Physics"
        or physics["actuator_body"] != "AnimatableBody3D"
        or physics["response_body"] != "RigidBody3D"
    ):
        raise SmokeError("semantic contact physics backend or body types are not exact")
    exact_booleans = {
        "actuator_sync_to_physics": True,
        "response_can_sleep": False,
        "response_rotation_locked": True,
        "response_contact_monitor": True,
        "one_shape_per_contact_body": True,
    }
    for key, expected in exact_booleans.items():
        if type(physics.get(key)) is not bool or physics[key] is not expected:
            raise SmokeError(f"semantic contact physics configuration {key} is not runtime-derived")
    if type(physics["response_max_contacts_reported"]) is not int or physics["response_max_contacts_reported"] != 8:
        raise SmokeError("semantic contact physics configuration contact capacity is not runtime-derived")
    response_mass = _contact_scalar(physics["response_mass"], "semantic contact physics configuration response_mass")
    response_gravity_scale = _contact_scalar(
        physics["response_gravity_scale"], "semantic contact physics configuration response_gravity_scale"
    )
    if response_mass != 1.0 or response_gravity_scale != 0.0:
        raise SmokeError("semantic contact physics mass or gravity configuration is not exact")


def _validate_contact_report(
    report: dict[str, Any],
    contact_command: dict[str, Any],
    contact_identity: dict[str, Any],
) -> dict[str, Any]:
    evidence = _contact_evidence_from_report(report)
    if set(evidence) != CONTACT_EVIDENCE_KEYS:
        raise SmokeError("Godot semantic contact evidence has unexpected or missing fields")
    if not _exact_json_equal(evidence["command_identity"], contact_identity):
        raise SmokeError("Godot semantic contact command identity is missing or ambiguous")
    targets = evidence["targets"]
    if not _exact_json_equal(targets, contact_command["targets"]):
        raise SmokeError("Godot semantic contact targets are missing, reordered, or mismatched")
    source_pose_command = evidence["source_pose_command"]
    if not _exact_json_equal(source_pose_command, contact_command["source_pose_command"]):
        raise SmokeError("Godot semantic contact source pose identity is mismatched")
    mapping_revision = evidence["mapping_revision"]
    if mapping_revision != CONTACT_MAPPING_REVISION:
        raise SmokeError("Godot semantic contact mapping revision is invalid")
    interaction = evidence["interaction"]
    if not _exact_json_equal(interaction, CONTACT_INTERACTION):
        raise SmokeError("Godot semantic contact interaction is missing or reordered")
    _validate_contact_mapping(evidence, contact_command)
    _validate_contact_physics(evidence)
    trace_by_tick = _validate_contact_ticks(evidence)
    strongest_sample = _validate_contact_impulses(evidence, trace_by_tick)
    _validate_contact_response(evidence, strongest_sample, trace_by_tick)
    return strongest_sample


def _validate_deformation_capture_destination(capture_path: Path) -> Path:
    capture_path = neutral_smoke._require_absolute(capture_path, "deformation capture directory")
    neutral_smoke._reject_symlink_path_components(capture_path, "deformation capture directory")
    if capture_path.exists() or capture_path.is_symlink():
        raise SmokeError(f"deformation capture directory must not already exist: {capture_path}")
    if not capture_path.parent.is_dir():
        raise SmokeError(f"deformation capture parent directory is unavailable: {capture_path.parent}")
    broad_destinations = {
        Path(capture_path.anchor),
        Path("/tmp"),
        Path("/var/tmp"),
        Path.home(),
        REPOSITORY_ROOT,
        Path.cwd(),
    }
    if capture_path in broad_destinations or len(capture_path.parts) <= 2:
        raise SmokeError(f"deformation capture directory is too broad or unsafe: {capture_path}")
    return capture_path


def _decode_deformation_png(data: bytes, file_name: str) -> bytes:
    if not isinstance(data, bytes) or not data:
        raise SmokeError(f"deformation capture {file_name} is empty")
    if len(data) > DEFORMATION_CAPTURE_MAX_BYTES:
        raise SmokeError(f"deformation capture {file_name} exceeds the bounded byte limit")
    if len(data) < 33 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise SmokeError(f"deformation capture {file_name} is not a PNG")
    if int.from_bytes(data[8:12], "big") != 13 or data[12:16] != b"IHDR":
        raise SmokeError(f"deformation capture {file_name} does not begin with an IHDR chunk")
    try:
        with Image.open(BytesIO(data)) as image:
            if image.format != "PNG":
                raise SmokeError(f"deformation capture {file_name} is not a PNG according to Pillow")
            image.verify()
        with Image.open(BytesIO(data)) as image:
            image.load()
            if image.format != "PNG":
                raise SmokeError(f"deformation capture {file_name} is not a PNG according to Pillow")
            width, height = image.size
            if width != DEFORMATION_CAPTURE_WIDTH or height != DEFORMATION_CAPTURE_HEIGHT:
                raise SmokeError(
                    f"deformation capture {file_name} dimensions are {width}x{height}, "
                    f"expected {DEFORMATION_CAPTURE_WIDTH}x{DEFORMATION_CAPTURE_HEIGHT}"
                )
            decoded = image.convert("RGBA").tobytes()
    except SmokeError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as exc:
        raise SmokeError(
            f"deformation capture {file_name} could not be decoded by Pillow: "
            f"{type(exc).__name__}: {exc}"
        ) from exc
    expected_bytes = DEFORMATION_CAPTURE_WIDTH * DEFORMATION_CAPTURE_HEIGHT * 4
    if len(decoded) != expected_bytes:
        raise SmokeError(
            f"deformation capture {file_name} decoded to an unexpected byte count: "
            f"observed={len(decoded)} expected={expected_bytes}"
        )
    return decoded


def _validate_deformation_png(data: bytes, file_name: str) -> None:
    _decode_deformation_png(data, file_name)


def _decoded_capture_metrics(decoded: bytes) -> dict[str, int]:
    pixels = Counter(decoded[offset : offset + 4] for offset in range(0, len(decoded), 4))
    dominant_count = max(pixels.values(), default=0)
    return {
        "pixel_count": len(decoded) // 4,
        "unique_rgba_pixels": len(pixels),
        "non_dominant_pixels": len(decoded) // 4 - dominant_count,
    }


def _decoded_capture_difference(left: bytes, right: bytes) -> dict[str, float | int]:
    changed_pixels = 0
    total_abs_channel_delta = 0
    max_channel_delta = 0
    for offset in range(0, len(left), 4):
        channel_deltas = [abs(left[offset + channel] - right[offset + channel]) for channel in range(4)]
        if any(channel_deltas):
            changed_pixels += 1
        total_abs_channel_delta += sum(channel_deltas)
        max_channel_delta = max(max_channel_delta, max(channel_deltas))
    pixel_count = len(left) // 4
    return {
        "changed_pixels": changed_pixels,
        "changed_pixel_fraction": changed_pixels / pixel_count if pixel_count else 0.0,
        "total_abs_channel_delta": total_abs_channel_delta,
        "max_channel_delta": max_channel_delta,
    }


def _deformation_capsule_basis(endpoint_a: list[float], endpoint_b: list[float]) -> tuple[list[float], list[float], list[float]]:
    """Reconstruct GDScript's deterministic basis for a capsule's local Y axis."""
    direction = [right - left for left, right in zip(endpoint_a, endpoint_b)]
    length = math.sqrt(sum(value * value for value in direction))
    if not math.isfinite(length) or length <= 1.0e-12:
        raise SmokeError("semantic deformation response capsule cannot define a deterministic basis")
    y_axis = [value / length for value in direction]
    reference = [0.0, 0.0, 1.0]
    if abs(sum(left * right for left, right in zip(y_axis, reference))) > 0.9:
        reference = [1.0, 0.0, 0.0]

    def cross(left: list[float], right: list[float]) -> list[float]:
        return [
            left[1] * right[2] - left[2] * right[1],
            left[2] * right[0] - left[0] * right[2],
            left[0] * right[1] - left[1] * right[0],
        ]

    def normalized(vector: list[float]) -> list[float]:
        magnitude = math.sqrt(sum(value * value for value in vector))
        if not math.isfinite(magnitude) or magnitude <= 1.0e-12:
            raise SmokeError("semantic deformation response capsule basis is degenerate")
        return [value / magnitude for value in vector]

    x_axis = normalized(cross(y_axis, reference))
    z_axis = normalized(cross(x_axis, y_axis))
    return x_axis, y_axis, z_axis


def _reconstruct_deformation_baseline_vertices(
    radius: float,
    length: float,
    basis: tuple[list[float], list[float], list[float]],
) -> list[list[float]]:
    """Reconstruct the transformed GDScript open-cylinder vertex order."""
    x_axis, y_axis, z_axis = basis
    half_length = 0.5 * length
    vertices: list[list[float]] = []
    for axial_index in range(DEFORMATION_AXIAL_SEGMENTS + 1):
        axial_fraction = float(axial_index) / float(DEFORMATION_AXIAL_SEGMENTS)
        axial = (-half_length) + (2.0 * half_length) * axial_fraction
        for radial_index in range(DEFORMATION_RADIAL_SEGMENTS):
            angle = 2.0 * math.pi * float(radial_index) / float(DEFORMATION_RADIAL_SEGMENTS)
            radial_x = math.cos(angle)
            radial_z = math.sin(angle)
            local = [radial_x * radius, axial, radial_z * radius]
            vertices.append(
                [
                    x_axis[axis] * local[0] + y_axis[axis] * local[1] + z_axis[axis] * local[2]
                    for axis in range(3)
                ]
            )
    return vertices


def _render_matrix_point(matrix: list[float], point: list[float]) -> list[float]:
    return [
        matrix[0] * point[0] + matrix[1] * point[1] + matrix[2] * point[2] + matrix[3],
        matrix[4] * point[0] + matrix[5] * point[1] + matrix[6] * point[2] + matrix[7],
        matrix[8] * point[0] + matrix[9] * point[1] + matrix[10] * point[2] + matrix[11],
    ]


def _render_matrix_inverse_point(matrix: list[float], point: list[float]) -> list[float]:
    relative = [point[index] - matrix[index * 4 + 3] for index in range(3)]
    return [
        matrix[0] * relative[0] + matrix[4] * relative[1] + matrix[8] * relative[2],
        matrix[1] * relative[0] + matrix[5] * relative[1] + matrix[9] * relative[2],
        matrix[2] * relative[0] + matrix[6] * relative[1] + matrix[10] * relative[2],
    ]


def _render_identity_matrix() -> list[float]:
    return [
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
    ]


def _validate_render_matrix(value: Any, where: str) -> list[float]:
    if not isinstance(value, list) or len(value) != 16 or any(not _finite_number(item) for item in value):
        raise SmokeError(f"{where} must be a finite 4x4 matrix")
    matrix = [float(item) for item in value]
    if any(abs(matrix[index] - expected) > TOLERANCE for index, expected in ((12, 0.0), (13, 0.0), (14, 0.0), (15, 1.0))):
        raise SmokeError(f"{where} is not homogeneous")
    columns = (
        [matrix[index] for index in (0, 4, 8)],
        [matrix[index] for index in (1, 5, 9)],
        [matrix[index] for index in (2, 6, 10)],
    )
    for axis_index, axis in enumerate(columns):
        length = math.sqrt(sum(component * component for component in axis))
        if not math.isfinite(length) or abs(length - 1.0) > NORMAL_TOLERANCE:
            raise SmokeError(f"{where} basis axis {axis_index} is not normalized")
    for left_index, right_index in ((0, 1), (0, 2), (1, 2)):
        dot = sum(left * right for left, right in zip(columns[left_index], columns[right_index]))
        if not math.isfinite(dot) or abs(dot) > NORMAL_TOLERANCE:
            raise SmokeError(f"{where} basis is not orthogonal")
    determinant = (
        columns[0][0] * (columns[1][1] * columns[2][2] - columns[1][2] * columns[2][1])
        - columns[1][0] * (columns[0][1] * columns[2][2] - columns[0][2] * columns[2][1])
        + columns[2][0] * (columns[0][1] * columns[1][2] - columns[0][2] * columns[1][1])
    )
    if not math.isfinite(determinant) or abs(determinant - 1.0) > NORMAL_TOLERANCE:
        raise SmokeError(f"{where} basis is not a proper orthonormal rotation")
    return matrix


def _render_matrix_close(left: list[float], right: list[float], where: str) -> None:
    if any(abs(first - second) > TOLERANCE for first, second in zip(left, right)):
        raise SmokeError(f"{where} is not cross-linked to the expected transform")


def _render_first_positive_contact_sample(contact_evidence: dict[str, Any]) -> dict[str, Any]:
    tick_evidence = contact_evidence.get("contact_tick_evidence")
    if not isinstance(tick_evidence, list):
        raise SmokeError("semantic render/collision contact tick evidence is missing")
    trace_by_tick = {
        record["tick"]: record
        for record in tick_evidence
        if isinstance(record, dict) and type(record.get("tick")) is int
    }
    impulses = contact_evidence.get("solver_impulses")
    if not isinstance(impulses, list):
        raise SmokeError("semantic render/collision contact samples are missing")
    positive: list[tuple[int, float, int, dict[str, Any]]] = []
    for impulse_record in impulses:
        if not isinstance(impulse_record, dict) or not isinstance(impulse_record.get("contact_samples"), list):
            raise SmokeError("semantic render/collision contact samples are malformed")
        for sample in impulse_record["contact_samples"]:
            if not isinstance(sample, dict):
                raise SmokeError("semantic render/collision contact sample is malformed")
            tick = sample.get("tick")
            trace = trace_by_tick.get(tick)
            if (
                type(tick) is not int
                or trace is None
                or sample.get("phase") != "contact"
                or trace.get("phase") != "contact"
                or type(trace.get("contact_count")) is not int
                or trace["contact_count"] <= 0
            ):
                continue
            impulse = _contact_vector(sample.get("impulse"), "semantic render/collision contact sample impulse")
            impulse_length = math.sqrt(sum(component * component for component in impulse))
            contact_index = sample.get("contact_index")
            if type(contact_index) is not int or contact_index < 0:
                raise SmokeError("semantic render/collision contact sample index is invalid")
            if impulse_length > 0.0:
                positive.append((tick, impulse_length, contact_index, sample))
    if not positive:
        raise SmokeError("semantic render/collision has no positive contact sample")
    # The producer selects the strongest sample within the first actual
    # positive-contact tick. A lower contact index is the deterministic tie
    # break, matching the runtime's ordered contact iteration.
    return min(positive, key=lambda candidate: (candidate[0], -candidate[1], candidate[2]))[3]


def _render_collision_metrics(
    vertices: list[list[float]],
    endpoint_a: list[float],
    endpoint_b: list[float],
    radius: float,
    falloff_weights: list[Any],
    where: str,
) -> dict[str, float]:
    if len(vertices) != RENDER_COLLISION_COHERENCE_VERTEX_COUNT:
        raise SmokeError(f"{where} vertices are incomplete")
    segment = [right - left for left, right in zip(endpoint_a, endpoint_b)]
    segment_length_squared = sum(component * component for component in segment)
    if not math.isfinite(segment_length_squared) or segment_length_squared <= 1.0e-24:
        raise SmokeError(f"{where} capsule segment is degenerate")
    clearances: list[float] = []
    outside_clearances: list[float] = []
    for index, vertex in enumerate(vertices):
        point = _contact_vector(vertex, f"{where} vertex {index}")
        offset = [point[axis] - endpoint_a[axis] for axis in range(3)]
        fraction = sum(offset[axis] * segment[axis] for axis in range(3)) / segment_length_squared
        fraction = min(1.0, max(0.0, fraction))
        closest = [endpoint_a[axis] + fraction * segment[axis] for axis in range(3)]
        distance = math.sqrt(sum((point[axis] - closest[axis]) ** 2 for axis in range(3)))
        clearance = distance - radius
        if not math.isfinite(clearance):
            raise SmokeError(f"{where} vertex {index} clearance is non-finite")
        clearances.append(clearance)
        if index < len(falloff_weights) and float(falloff_weights[index]) == 0.0:
            outside_clearances.append(clearance)
    return {
        "maximum_absolute_side_clearance": max((abs(value) for value in clearances), default=0.0),
        "maximum_outward_clearance": max((max(value, 0.0) for value in clearances), default=0.0),
        "maximum_inward_penetration": max((max(-value, 0.0) for value in clearances), default=0.0),
        "outside_falloff_max_penetration": max((max(-value, 0.0) for value in outside_clearances), default=0.0),
    }


def _reconstruct_contact_deformation(
    sample: dict[str, Any],
    response_transform: list[float],
    radius: float,
    length: float,
    capsule_basis: tuple[list[float], list[float], list[float]],
    reference_vertices: list[list[float]],
    where: str,
) -> tuple[list[float], list[float], list[float], list[float], list[list[float]]]:
    runtime_contact_point = _contact_vector(sample.get("point"), f"{where} runtime contact point")
    normal = _contact_vector(sample.get("normal"), f"{where} contact normal")
    normal_length = math.sqrt(sum(value * value for value in normal))
    if not math.isfinite(normal_length) or normal_length <= 1.0e-12:
        raise SmokeError(f"{where} contact normal is zero or nonfinite")
    normalized_normal = [value / normal_length for value in normal]
    local_contact_point = _render_matrix_inverse_point(response_transform, runtime_contact_point)
    surface_contact_point = [
        sum(component * axis_component for component, axis_component in zip(local_contact_point, axis))
        for axis in capsule_basis
    ]
    radial_contact = [surface_contact_point[0], 0.0, surface_contact_point[2]]
    radial_length = math.sqrt(sum(value * value for value in radial_contact))
    if not math.isfinite(radial_length) or radial_length <= 1.0e-9:
        raise SmokeError(f"{where} contact geometry cannot define a radial outward direction")
    radial_outward = [radial_contact[0] / radial_length, 0.0, radial_contact[2] / radial_length]
    projected_center_local = [
        radial_outward[0] * radius,
        min(max(surface_contact_point[1], -0.5 * length), 0.5 * length),
        radial_outward[2] * radius,
    ]
    deformation_center = [
        sum(capsule_basis[axis][component] * projected_center_local[axis] for axis in range(3))
        for component in range(3)
    ]
    toward_sleeve_center = [-value for value in deformation_center]
    center_length = math.sqrt(sum(value * value for value in toward_sleeve_center))
    if not math.isfinite(center_length) or center_length <= 1.0e-12:
        raise SmokeError(f"{where} projected sleeve center cannot define an inward direction")
    alignment = abs(sum(left * right for left, right in zip(normalized_normal, toward_sleeve_center))) / center_length
    if not math.isfinite(alignment) or alignment < DEFORMATION_MIN_CONTACT_NORMAL_CENTER_ALIGNMENT:
        raise SmokeError(f"{where} contact normal does not define the fixed inward direction")
    inward = normalized_normal if sum(left * right for left, right in zip(normalized_normal, toward_sleeve_center)) > 0.0 else [-value for value in normalized_normal]

    falloff_radius = radius * DEFORMATION_FALLOFF_RADIUS_RATIO
    if not math.isfinite(falloff_radius) or falloff_radius <= 0.0:
        raise SmokeError(f"{where} compact falloff radius is invalid")
    raw_weights = []
    for reference_vertex in reference_vertices:
        distance = math.sqrt(
            sum((float(coordinate) - float(center_coordinate)) ** 2 for coordinate, center_coordinate in zip(reference_vertex, deformation_center))
        )
        raw_weights.append(max(0.0, 1.0 - distance / falloff_radius) ** 2 if distance < falloff_radius else 0.0)
    weight_max = max(raw_weights, default=0.0)
    if not math.isfinite(weight_max) or weight_max <= 0.0:
        raise SmokeError(f"{where} compact falloff has no positive vertex weight")
    weights = [value / weight_max for value in raw_weights]
    if (
        not any(value > 0.0 for value in weights)
        or not any(value == 0.0 for value in weights)
        or abs(max(weights) - 1.0) > TOLERANCE
        or sum(value > 0.0 for value in weights) / len(weights) > DEFORMATION_MAX_AFFECTED_FRACTION
    ):
        raise SmokeError(f"{where} compact falloff is not localized with a unit peak")
    absolute_depth = radius * DEFORMATION_NORMALIZED_PEAK_DEPTH
    vertices = [
        [float(coordinate) + inward[axis] * absolute_depth * weight for axis, coordinate in enumerate(reference_vertex)]
        for reference_vertex, weight in zip(reference_vertices, weights)
    ]
    return local_contact_point, deformation_center, inward, weights, vertices


def _read_deformation_capture_bytes(capture_directory: Path) -> dict[str, bytes]:
    if not capture_directory.is_dir() or capture_directory.is_symlink():
        raise SmokeError("Godot deformation capture directory is missing or unsafe")
    try:
        entries = list(capture_directory.iterdir())
    except OSError as exc:
        raise SmokeError(f"Godot deformation captures cannot be enumerated: {type(exc).__name__}: {exc}") from exc
    if {entry.name for entry in entries} != set(DEFORMATION_CAPTURE_NAMES):
        raise SmokeError("Godot deformation capture directory does not contain exactly the three required PNGs")
    captures: dict[str, bytes] = {}
    for file_name in DEFORMATION_CAPTURE_NAMES:
        path = capture_directory / file_name
        if path.is_symlink() or not path.is_file():
            raise SmokeError(f"Godot deformation capture {file_name} is not a regular file")
        try:
            if path.lstat().st_size > DEFORMATION_CAPTURE_MAX_BYTES:
                raise SmokeError(f"deformation capture {file_name} exceeds the bounded byte limit")
            data = path.read_bytes()
        except SmokeError:
            raise
        except OSError as exc:
            raise SmokeError(f"Godot deformation capture {file_name} cannot be read: {type(exc).__name__}: {exc}") from exc
        _validate_deformation_png(data, file_name)
        captures[file_name] = data
    return captures


def _fsync_directory(directory: Path) -> None:
    try:
        descriptor = os.open(directory, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


def _rename_directory_noreplace(source: Path, destination: Path) -> None:
    """Atomically publish a directory without replacing a concurrent destination."""
    if sys.platform != "linux":
        raise SmokeError("atomic no-overwrite deformation capture publication requires Linux renameat2")
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        renameat2 = libc.renameat2
    except (AttributeError, OSError) as exc:
        raise SmokeError("atomic no-overwrite deformation capture publication is unavailable") from exc
    renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    renameat2.restype = ctypes.c_int
    result = renameat2(
        -100,
        os.fsencode(source),
        -100,
        os.fsencode(destination),
        1,
    )
    if result == 0:
        return
    error_number = ctypes.get_errno()
    if error_number == errno.EEXIST:
        raise SmokeError(f"deformation capture directory already exists: {destination}")
    raise OSError(error_number, os.strerror(error_number), destination)


def _publish_deformation_captures(capture_path: Path, capture_bytes: dict[str, bytes]) -> None:
    capture_path = _validate_deformation_capture_destination(capture_path)
    if set(capture_bytes) != set(DEFORMATION_CAPTURE_NAMES):
        raise SmokeError("staged deformation captures are incomplete or contain unexpected files")
    for file_name in DEFORMATION_CAPTURE_NAMES:
        _validate_deformation_png(capture_bytes[file_name], file_name)
    temporary_path: Path | None = None
    try:
        temporary_path = Path(
            tempfile.mkdtemp(prefix=f".{capture_path.name}-", dir=capture_path.parent)
        )
        for file_name in DEFORMATION_CAPTURE_NAMES:
            file_path = temporary_path / file_name
            with file_path.open("xb") as output:
                output.write(capture_bytes[file_name])
                output.flush()
                os.fsync(output.fileno())
        _fsync_directory(temporary_path)
        _rename_directory_noreplace(temporary_path, capture_path)
        temporary_path = None
        _fsync_directory(capture_path.parent)
    except SmokeError:
        raise
    except OSError as exc:
        raise SmokeError(f"deformation captures could not be published: {type(exc).__name__}: {exc}") from exc
    finally:
        if temporary_path is not None:
            shutil.rmtree(temporary_path, ignore_errors=True)


def _rollback_deformation_captures(capture_path: Path, capture_bytes: dict[str, bytes]) -> None:
    """Remove only the exact capture set published by this run after report failure."""
    if not capture_path.exists() and not capture_path.is_symlink():
        return
    if capture_path.is_symlink() or not capture_path.is_dir():
        raise SmokeError("deformation capture rollback found an unsafe publication target")
    try:
        entries = list(capture_path.iterdir())
        if {entry.name for entry in entries} != set(DEFORMATION_CAPTURE_NAMES):
            raise SmokeError("deformation capture rollback refused to remove an unexpected directory")
        for file_name in DEFORMATION_CAPTURE_NAMES:
            path = capture_path / file_name
            if path.is_symlink() or not path.is_file() or path.read_bytes() != capture_bytes[file_name]:
                raise SmokeError("deformation capture rollback refused to remove changed or unsafe capture bytes")
        for file_name in DEFORMATION_CAPTURE_NAMES:
            (capture_path / file_name).unlink()
        capture_path.rmdir()
        _fsync_directory(capture_path.parent)
    except SmokeError:
        raise
    except OSError as exc:
        raise SmokeError(f"deformation capture rollback failed: {type(exc).__name__}: {exc}") from exc


def _publish_deformation_result(
    report_path: Path,
    report: dict[str, Any],
    deformation_captures_path: Path | None,
    staged_deformation_captures: dict[str, bytes] | None,
) -> None:
    """Publish captures before the success report, rolling them back on report failure."""
    if deformation_captures_path is None:
        neutral_smoke._publish_report(report_path, report)
        return
    if staged_deformation_captures is None:
        raise SmokeError("semantic deformation captures were not retained in memory")
    _publish_deformation_captures(deformation_captures_path, staged_deformation_captures)
    try:
        neutral_smoke._publish_report(report_path, report)
    except Exception as exc:
        try:
            _rollback_deformation_captures(deformation_captures_path, staged_deformation_captures)
        except Exception as rollback_exc:
            raise SmokeError(
                "canonical deformation report publication failed and capture rollback also failed: "
                f"report_error={type(exc).__name__}: {exc}; "
                f"rollback_error={type(rollback_exc).__name__}: {rollback_exc}"
            ) from rollback_exc
        raise


def _validate_deformation_report(
    report: dict[str, Any],
    strongest_contact_sample: dict[str, Any],
) -> None:
    if "semantic_deformation" not in report:
        raise SmokeError("Godot report is missing semantic deformation evidence")
    if DEFORMATION_REPORT_ALIAS_KEYS.intersection(report):
        raise SmokeError("Godot report contains unsupported semantic deformation aliases")
    evidence = report["semantic_deformation"]
    expected_keys = {
        "boundary",
        "target_index",
        "source_bone_id",
        "source_shape_index",
        "runtime_shape_index",
        "surface",
        "drive",
        "states",
        "captures",
    }
    if not isinstance(evidence, dict) or set(evidence) != expected_keys:
        raise SmokeError("Godot semantic deformation evidence has unexpected or missing fields")
    if evidence["boundary"] != DEFORMATION_REPORT_BOUNDARY:
        raise SmokeError("Godot semantic deformation boundary is invalid")
    if (
        type(evidence["target_index"]) is not int
        or evidence["target_index"] != 1
        or evidence["source_bone_id"] != CONTACT_BONE_IDS[1]
        or type(evidence["source_shape_index"]) is not int
        or evidence["source_shape_index"] != CONTACT_SHAPE_INDICES[1]
        or type(evidence["runtime_shape_index"]) is not int
        or evidence["runtime_shape_index"] != CONTACT_RUNTIME_SHAPE_INDICES[1]
    ):
        raise SmokeError("Godot semantic deformation target or capsule lineage is invalid")

    contact_evidence = report.get("semantic_contact")
    if not isinstance(contact_evidence, dict):
        raise SmokeError("Godot semantic deformation requires the validated semantic contact evidence")
    participants = contact_evidence.get("participants")
    if not isinstance(participants, list) or len(participants) != len(CONTACT_PARTICIPANTS):
        raise SmokeError("Godot semantic deformation contact lineage is aggregate-only")
    response_participant = participants[1]
    if not isinstance(response_participant, dict):
        raise SmokeError("Godot semantic deformation response participant is invalid")
    posed_proxy = response_participant.get("posed_proxy")
    if not isinstance(posed_proxy, dict):
        raise SmokeError("Godot semantic deformation response capsule evidence is missing")
    radius = _contact_scalar(posed_proxy.get("radius"), "semantic deformation response capsule radius")
    if radius <= 0.0:
        raise SmokeError("semantic deformation response capsule radius is not positive")
    endpoint_a = _contact_vector(posed_proxy.get("a"), "semantic deformation response capsule endpoint a")
    endpoint_b = _contact_vector(posed_proxy.get("b"), "semantic deformation response capsule endpoint b")
    baseline_length = math.sqrt(sum((right - left) ** 2 for left, right in zip(endpoint_a, endpoint_b)))
    if not math.isfinite(baseline_length) or baseline_length <= 0.0:
        raise SmokeError("semantic deformation response capsule segment length is invalid")
    capsule_basis = _deformation_capsule_basis(endpoint_a, endpoint_b)

    surface = evidence["surface"]
    surface_keys = {
        "kind",
        "attachment",
        "collision_mode",
        "axial_segments",
        "radial_segments",
        "vertex_count",
        "triangle_count",
        "baseline_radius",
        "baseline_length",
    }
    if not isinstance(surface, dict) or set(surface) != surface_keys:
        raise SmokeError("Godot semantic deformation surface evidence has unexpected or missing fields")
    if (
        surface["kind"] != DEFORMATION_SURFACE_KIND
        or surface["attachment"] != DEFORMATION_SURFACE_ATTACHMENT
        or surface["collision_mode"] != DEFORMATION_SURFACE_COLLISION_MODE
        or type(surface["axial_segments"]) is not int
        or surface["axial_segments"] != DEFORMATION_AXIAL_SEGMENTS
        or type(surface["radial_segments"]) is not int
        or surface["radial_segments"] != DEFORMATION_RADIAL_SEGMENTS
        or type(surface["vertex_count"]) is not int
        or surface["vertex_count"] != DEFORMATION_VERTEX_COUNT
        or type(surface["triangle_count"]) is not int
        or surface["triangle_count"] != DEFORMATION_TRIANGLE_COUNT
    ):
        raise SmokeError("Godot semantic deformation surface topology or collision disclosure is invalid")
    surface_radius = _contact_scalar(surface["baseline_radius"], "semantic deformation surface baseline radius")
    surface_length = _contact_scalar(surface["baseline_length"], "semantic deformation surface baseline length")
    if abs(surface_radius - radius) > TOLERANCE or abs(surface_length - baseline_length) > TOLERANCE:
        raise SmokeError("Godot semantic deformation surface is not derived from the selected response capsule")

    drive = evidence["drive"]
    drive_keys = {
        "kind",
        "normalized_peak_depth",
        "absolute_peak_depth",
        "falloff_radius_ratio",
        "peak_tick",
        "contact_sample_tick",
        "contact_sample_index",
        "sample_response_transform",
        "runtime_contact_point",
        "local_contact_point",
        "local_deformation_center",
        "local_inward_direction",
        "falloff_weights",
    }
    if not isinstance(drive, dict) or set(drive) != drive_keys:
        raise SmokeError("Godot semantic deformation drive evidence has unexpected or missing fields")
    normalized_depth = _contact_scalar(
        drive["normalized_peak_depth"], "semantic deformation normalized peak depth"
    )
    absolute_depth = _contact_scalar(drive["absolute_peak_depth"], "semantic deformation absolute peak depth")
    falloff_ratio = _contact_scalar(drive["falloff_radius_ratio"], "semantic deformation falloff radius ratio")
    if (
        drive["kind"] != DEFORMATION_DRIVE_KIND
        or abs(normalized_depth - DEFORMATION_NORMALIZED_PEAK_DEPTH) > TOLERANCE
        or abs(absolute_depth - radius * DEFORMATION_NORMALIZED_PEAK_DEPTH) > TOLERANCE
        or abs(falloff_ratio - DEFORMATION_FALLOFF_RADIUS_RATIO) > TOLERANCE
    ):
        raise SmokeError("Godot semantic deformation drive is not the fixed moderate local press")
    peak_tick = drive["peak_tick"]
    contact_sample_tick = drive["contact_sample_tick"]
    contact_sample_index = drive["contact_sample_index"]
    if (
        type(peak_tick) is not int
        or peak_tick <= 0
        or type(contact_sample_tick) is not int
        or contact_sample_tick != strongest_contact_sample["tick"]
        or peak_tick != contact_sample_tick
        or type(contact_sample_index) is not int
        or contact_sample_index != strongest_contact_sample["contact_index"]
    ):
        raise SmokeError("Godot semantic deformation peak is not attributed to the positive contact sample")
    runtime_contact_point = _contact_vector(
        drive["runtime_contact_point"], "semantic deformation runtime contact point"
    )
    local_contact_point = _contact_vector(drive["local_contact_point"], "semantic deformation local contact point")
    local_deformation_center = _contact_vector(
        drive["local_deformation_center"],
        "semantic deformation local projected sleeve center",
    )
    inward = _contact_vector(drive["local_inward_direction"], "semantic deformation local inward direction")
    inward_length = math.sqrt(sum(value * value for value in inward))
    if not math.isfinite(inward_length) or abs(inward_length - 1.0) > NORMAL_TOLERANCE:
        raise SmokeError("Godot semantic deformation inward direction is not normalized")
    strongest_normal = _contact_vector(
        strongest_contact_sample.get("normal"),
        "semantic deformation strongest runtime contact normal",
    )
    strongest_normal_length = math.sqrt(sum(value * value for value in strongest_normal))
    if not math.isfinite(strongest_normal_length) or strongest_normal_length <= 1.0e-12:
        raise SmokeError("Godot semantic deformation strongest runtime contact normal is zero or nonfinite")
    normalized_strongest_normal = [value / strongest_normal_length for value in strongest_normal]
    normalized_inward = [value / inward_length for value in inward]
    strongest_point = _contact_vector(
        strongest_contact_sample.get("point"),
        "semantic deformation strongest runtime contact point",
    )
    if any(abs(left - right) > TOLERANCE for left, right in zip(runtime_contact_point, strongest_point)):
        raise SmokeError("Godot semantic deformation runtime contact point is not the retained runtime contact sample")
    sample_response_transform = drive["sample_response_transform"]
    if not isinstance(sample_response_transform, list) or len(sample_response_transform) != 16 or any(
        not _finite_number(value) for value in sample_response_transform
    ):
        raise SmokeError("Godot semantic deformation sample response transform is invalid")
    if [float(value) for value in sample_response_transform[12:16]] != [0.0, 0.0, 0.0, 1.0]:
        raise SmokeError("Godot semantic deformation sample response transform is not homogeneous")
    basis_columns = (
        [float(sample_response_transform[index]) for index in (0, 4, 8)],
        [float(sample_response_transform[index]) for index in (1, 5, 9)],
        [float(sample_response_transform[index]) for index in (2, 6, 10)],
    )
    for axis_index, axis in enumerate(basis_columns):
        axis_length = math.sqrt(sum(value * value for value in axis))
        if abs(axis_length - 1.0) > NORMAL_TOLERANCE:
            raise SmokeError(f"Godot semantic deformation response basis axis {axis_index} is not normalized")
    if any(
        abs(sum(left * right for left, right in zip(basis_columns[left_index], basis_columns[right_index])))
        > NORMAL_TOLERANCE
        for left_index, right_index in ((0, 1), (0, 2), (1, 2))
    ):
        raise SmokeError("Godot semantic deformation response basis is not orthogonal")
    contact_origin = [float(sample_response_transform[index]) for index in (3, 7, 11)]
    runtime_relative = [value - origin for value, origin in zip(runtime_contact_point, contact_origin)]
    expected_local_contact_point = [
        sum(value * axis_component for value, axis_component in zip(runtime_relative, axis))
        for axis in basis_columns
    ]
    if any(
        abs(left - right) > TOLERANCE
        for left, right in zip(local_contact_point, expected_local_contact_point)
    ):
        raise SmokeError("Godot semantic deformation local contact point is not transformed from the runtime sample")
    normal_line_alignment = abs(
        sum(left * right for left, right in zip(normalized_inward, normalized_strongest_normal))
    )
    if normal_line_alignment < DEFORMATION_MIN_NORMAL_LINE_ALIGNMENT:
        raise SmokeError(
            "Godot semantic deformation inward direction is not collinear with the strongest runtime contact "
            f"normal: observed_line_alignment={normal_line_alignment:.9g} "
            f"required>={DEFORMATION_MIN_NORMAL_LINE_ALIGNMENT:.9g}"
        )
    weights = drive["falloff_weights"]
    if not isinstance(weights, list) or len(weights) != DEFORMATION_VERTEX_COUNT:
        raise SmokeError("Godot semantic deformation falloff weights are incomplete or aggregate-only")
    if any(not _finite_number(value) or float(value) < 0.0 or float(value) > 1.0 for value in weights):
        raise SmokeError("Godot semantic deformation falloff weights are outside [0, 1]")
    if not any(float(value) > 0.0 for value in weights) or not any(float(value) == 0.0 for value in weights):
        raise SmokeError("Godot semantic deformation falloff does not prove affected and unaffected vertices")

    states = evidence["states"]
    if not isinstance(states, dict) or set(states) != {"reference", "peak", "recovered"}:
        raise SmokeError("Godot semantic deformation states are incomplete or reordered")
    state_values: dict[str, dict[str, Any]] = {}
    state_keys = {
        "tick",
        "normalized_depth",
        "vertices",
        "max_residual",
        "affected_vertex_count",
        "outside_falloff_max_residual",
    }
    for label in ("reference", "peak", "recovered"):
        state = states[label]
        if not isinstance(state, dict) or set(state) != state_keys:
            raise SmokeError(f"Godot semantic deformation {label} state has unexpected or missing fields")
        if type(state["tick"]) is not int or state["tick"] < 0:
            raise SmokeError(f"Godot semantic deformation {label} state tick is invalid")
        _contact_scalar(state["normalized_depth"], f"semantic deformation {label} normalized depth")
        vertices = state["vertices"]
        if not isinstance(vertices, list) or len(vertices) != DEFORMATION_VERTEX_COUNT:
            raise SmokeError(f"Godot semantic deformation {label} vertices are incomplete or aggregate-only")
        for index, vertex in enumerate(vertices):
            values = _contact_vector(vertex, f"semantic deformation {label} vertex {index}")
            if any(abs(value) > 1.0e6 for value in values):
                raise SmokeError(f"Godot semantic deformation {label} vertices are unbounded")
        max_residual = _contact_scalar(state["max_residual"], f"semantic deformation {label} max residual")
        affected_count = state["affected_vertex_count"]
        if type(affected_count) is not int or affected_count < 0 or affected_count > DEFORMATION_VERTEX_COUNT:
            raise SmokeError(f"Godot semantic deformation {label} affected vertex count is invalid")
        outside_residual = _contact_scalar(
            state["outside_falloff_max_residual"],
            f"semantic deformation {label} outside-falloff residual",
        )
        if max_residual < 0.0 or outside_residual < 0.0:
            raise SmokeError(f"Godot semantic deformation {label} residual metrics are negative")
        state_values[label] = state

    reference = state_values["reference"]["vertices"]
    peak = state_values["peak"]["vertices"]
    recovered = state_values["recovered"]["vertices"]
    expected_reference = _reconstruct_deformation_baseline_vertices(surface_radius, surface_length, capsule_basis)
    for index, (actual_vertex, expected_vertex) in enumerate(zip(reference, expected_reference)):
        if any(abs(float(actual) - float(expected)) > TOLERANCE for actual, expected in zip(actual_vertex, expected_vertex)):
            raise SmokeError(
                "Godot semantic deformation reference geometry is not the selected capsule-derived "
                f"16x32 open-cylinder baseline at vertex {index}: observed={actual_vertex} expected={expected_vertex}"
            )

    response_snapshots = contact_evidence.get("response", {}).get("snapshots")
    if not isinstance(response_snapshots, dict) or set(response_snapshots) != {"initial", "onset", "contact", "final"}:
        raise SmokeError("Godot semantic deformation response snapshots are incomplete or aliased")
    onset_snapshot = _validate_contact_snapshot(
        response_snapshots["onset"], "onset", "semantic deformation response onset"
    )
    first_positive_sample = _render_first_positive_contact_sample(contact_evidence)
    if onset_snapshot["tick"] != first_positive_sample["tick"]:
        raise SmokeError("Godot semantic deformation onset snapshot is not tied to the first positive contact sample")
    onset_transform = _validate_render_matrix(
        response_snapshots["onset"]["transform"], "semantic deformation onset response transform"
    )
    coherence = report.get("semantic_render_collision_coherence")
    coherence_states = coherence.get("states") if isinstance(coherence, dict) else None
    onset_coherence = next(
        (
            state
            for state in coherence_states
            if isinstance(state, dict) and state.get("state") == "contact_onset"
        ),
        None,
    ) if isinstance(coherence_states, list) else None
    if not isinstance(onset_coherence, dict):
        raise SmokeError("Godot semantic deformation onset coherence state is missing")
    onset_coherence_transform = _validate_render_matrix(
        onset_coherence.get("response_body_to_world"),
        "semantic deformation onset coherence response transform",
    )
    _render_matrix_close(
        onset_coherence_transform,
        onset_transform,
        "semantic deformation onset coherence response_body_to_world",
    )
    _local_onset_contact, _onset_center, _onset_inward, _onset_weights, expected_onset_vertices = _reconstruct_contact_deformation(
        first_positive_sample,
        onset_transform,
        surface_radius,
        surface_length,
        capsule_basis,
        expected_reference,
        "semantic deformation onset",
    )
    onset_vertices = onset_coherence.get("vertices")
    if not isinstance(onset_vertices, list) or len(onset_vertices) != DEFORMATION_VERTEX_COUNT:
        raise SmokeError("Godot semantic deformation onset coherence vertices are incomplete")
    for index, (actual_vertex, expected_vertex) in enumerate(zip(onset_vertices, expected_onset_vertices)):
        actual = _contact_vector(actual_vertex, f"semantic deformation onset coherence vertex {index}")
        if any(abs(left - right) > TOLERANCE for left, right in zip(actual, expected_vertex)):
            raise SmokeError(
                f"Godot semantic deformation onset vertex {index} is not reconstructed from the first positive contact sample"
            )
    if (
        state_values["reference"]["tick"] != 0
        or abs(float(state_values["reference"]["normalized_depth"])) > TOLERANCE
        or state_values["peak"]["tick"] != peak_tick
        or abs(float(state_values["peak"]["normalized_depth"]) - DEFORMATION_NORMALIZED_PEAK_DEPTH) > TOLERANCE
        or state_values["recovered"]["tick"] != DEFORMATION_RECOVERY_TICK
        or abs(float(state_values["recovered"]["normalized_depth"])) > TOLERANCE
    ):
        raise SmokeError("Godot semantic deformation state ticks or depths are not reference/peak/recovery")

    surface_contact_point = [
        sum(component * axis_component for component, axis_component in zip(local_contact_point, axis))
        for axis in capsule_basis
    ]
    radial_contact = [surface_contact_point[0], 0.0, surface_contact_point[2]]
    radial_contact_length = math.sqrt(sum(value * value for value in radial_contact))
    if not math.isfinite(radial_contact_length) or radial_contact_length <= 1.0e-9:
        raise SmokeError("Godot semantic deformation contact geometry cannot reconstruct a radial outward direction")
    radial_outward_local = [
        radial_contact[0] / radial_contact_length,
        0.0,
        radial_contact[2] / radial_contact_length,
    ]
    projected_center_local = [
        radial_outward_local[0] * surface_radius,
        min(max(surface_contact_point[1], -0.5 * surface_length), 0.5 * surface_length),
        radial_outward_local[2] * surface_radius,
    ]
    expected_deformation_center = [
        sum(capsule_basis[axis][component] * projected_center_local[axis] for axis in range(3))
        for component in range(3)
    ]
    if any(
        abs(left - right) > TOLERANCE
        for left, right in zip(local_deformation_center, expected_deformation_center)
    ):
        raise SmokeError("Godot semantic deformation center is not the nearest projected sleeve point")
    falloff_radius = surface_radius * DEFORMATION_FALLOFF_RADIUS_RATIO
    raw_expected_weights = []
    for reference_vertex in expected_reference:
        distance = math.sqrt(
            sum(
                (float(coordinate) - float(center_coordinate)) ** 2
                for coordinate, center_coordinate in zip(reference_vertex, local_deformation_center)
            )
        )
        raw_expected_weights.append(
            max(0.0, 1.0 - distance / falloff_radius) ** 2 if distance < falloff_radius else 0.0
        )
    expected_weight_max = max(raw_expected_weights, default=0.0)
    if not math.isfinite(expected_weight_max) or expected_weight_max <= 0.0:
        raise SmokeError("Godot semantic deformation reconstructed falloff has no positive vertex weight")
    expected_weights = [value / expected_weight_max for value in raw_expected_weights]
    if any(abs(float(actual) - expected) > TOLERANCE for actual, expected in zip(weights, expected_weights)):
        raise SmokeError("Godot semantic deformation falloff weights are not independently reconstructed")
    reconstructed_affected_count = sum(value > 0.0 for value in expected_weights)
    if (
        reconstructed_affected_count <= 0
        or reconstructed_affected_count >= DEFORMATION_VERTEX_COUNT
        or reconstructed_affected_count / DEFORMATION_VERTEX_COUNT > DEFORMATION_MAX_AFFECTED_FRACTION
        or abs(max(expected_weights) - 1.0) > TOLERANCE
    ):
        raise SmokeError("Godot semantic deformation reconstructed falloff is not localized with a unit peak")
    toward_sleeve_center = [-value for value in local_deformation_center]
    toward_sleeve_center_length = math.sqrt(sum(value * value for value in toward_sleeve_center))
    if not math.isfinite(toward_sleeve_center_length) or toward_sleeve_center_length <= 1.0e-12:
        raise SmokeError("Godot semantic deformation projected sleeve center cannot define an inward direction")
    normalized_toward_center = [value / toward_sleeve_center_length for value in toward_sleeve_center]
    inward_center_alignment = sum(left * right for left, right in zip(normalized_inward, normalized_toward_center))
    if inward_center_alignment < DEFORMATION_MIN_CONTACT_NORMAL_CENTER_ALIGNMENT:
        raise SmokeError(
            "Godot semantic deformation actual-normal direction does not point inward from the projected sleeve "
            f"center: observed_inward_alignment={inward_center_alignment:.9g} "
            f"required>={DEFORMATION_MIN_CONTACT_NORMAL_CENTER_ALIGNMENT:.9g}"
        )

    residuals: list[float] = []
    expected_affected_count = 0
    outside_max = 0.0
    for index, (reference_vertex, peak_vertex, weight) in enumerate(zip(reference, peak, weights)):
        residual = [float(right) - float(left) for left, right in zip(reference_vertex, peak_vertex)]
        expected = [float(component) * absolute_depth * float(weight) for component in inward]
        if any(abs(left - right) > TOLERANCE for left, right in zip(residual, expected)):
            raise SmokeError(f"Godot semantic deformation peak residual {index} is not contact-driven")
        residual_length = math.sqrt(sum(value * value for value in residual))
        residuals.append(residual_length)
        if float(weight) > 0.0:
            expected_affected_count += 1
        else:
            outside_max = max(outside_max, residual_length)
    max_residual = max(residuals, default=0.0)
    peak_state = state_values["peak"]
    if (
        expected_affected_count != reconstructed_affected_count
        or expected_affected_count >= DEFORMATION_VERTEX_COUNT
        or peak_state["affected_vertex_count"] != expected_affected_count
        or abs(float(peak_state["max_residual"]) - max_residual) > TOLERANCE
        or abs(float(peak_state["outside_falloff_max_residual"]) - outside_max) > TOLERANCE
            or abs(max_residual - absolute_depth) > TOLERANCE
            or outside_max > TOLERANCE
            or outside_max >= max_residual
        ):
        raise SmokeError("Godot semantic deformation peak metrics are inconsistent or not localized")

    for label, vertices in (("reference", reference), ("recovered", recovered)):
        residuals_to_reference = [
            math.sqrt(sum((float(right) - float(left)) ** 2 for left, right in zip(reference_vertex, right_vertex)))
            for reference_vertex, right_vertex in zip(reference, vertices)
        ]
        actual_max = max(residuals_to_reference, default=0.0)
        actual_count = sum(value > TOLERANCE for value in residuals_to_reference)
        actual_outside = max(
            (value for value, weight in zip(residuals_to_reference, weights) if float(weight) == 0.0),
            default=0.0,
        )
        state = state_values[label]
        if (
            abs(float(state["max_residual"]) - actual_max) > TOLERANCE
            or state["affected_vertex_count"] != actual_count
            or abs(float(state["outside_falloff_max_residual"]) - actual_outside) > TOLERANCE
            or actual_max > TOLERANCE
            or actual_outside > TOLERANCE
        ):
            raise SmokeError(f"Godot semantic deformation {label} recovery metrics are inconsistent")


def _validate_render_collision_coherence(
    report: dict[str, Any],
    strongest_contact_sample: dict[str, Any],
) -> None:
    if RENDER_COLLISION_COHERENCE_ALIAS_KEYS.intersection(report):
        raise SmokeError("Godot report contains unsupported semantic render/collision coherence aliases")
    if "semantic_render_collision_coherence" not in report:
        raise SmokeError("Godot report is missing semantic render/collision coherence evidence")
    coherence = report["semantic_render_collision_coherence"]
    if not isinstance(coherence, dict):
        raise SmokeError("Godot semantic render/collision coherence evidence is not an object")
    _validate_finite_report_json(coherence, "Godot semantic render/collision coherence")
    if set(coherence) != RENDER_COLLISION_COHERENCE_KEYS:
        raise SmokeError("Godot semantic render/collision coherence has unexpected or missing fields")
    if (
        coherence["schema"] != RENDER_COLLISION_COHERENCE_SCHEMA
        or coherence["boundary"] != RENDER_COLLISION_COHERENCE_BOUNDARY
        or coherence["frame"] != RENDER_COLLISION_COHERENCE_FRAME
        or coherence["collision_mode"] != RENDER_COLLISION_COHERENCE_COLLISION_MODE
        or coherence["falloff_source"] != RENDER_COLLISION_COHERENCE_FALLOFF_SOURCE
        or type(coherence["vertex_count"]) is not int
        or coherence["vertex_count"] != RENDER_COLLISION_COHERENCE_VERTEX_COUNT
        or not _exact_json_equal(coherence["state_order"], list(RENDER_COLLISION_COHERENCE_STATE_ORDER))
    ):
        raise SmokeError("Godot semantic render/collision coherence identity is invalid")

    contact_evidence = report.get("semantic_contact")
    deformation_evidence = report.get("semantic_deformation")
    if not isinstance(contact_evidence, dict) or not isinstance(deformation_evidence, dict):
        raise SmokeError("Godot semantic render/collision coherence is missing contact or deformation lineage")
    participants = contact_evidence.get("participants")
    if not isinstance(participants, list) or len(participants) != len(CONTACT_PARTICIPANTS):
        raise SmokeError("Godot semantic render/collision coherence contact lineage is incomplete")
    response_participant = participants[1]
    if not isinstance(response_participant, dict) or not isinstance(response_participant.get("posed_proxy"), dict):
        raise SmokeError("Godot semantic render/collision coherence selected posed proxy is missing")
    posed_proxy = response_participant["posed_proxy"]
    source_endpoint_a = _contact_vector(
        posed_proxy.get("a"), "semantic render/collision selected posed proxy endpoint a"
    )
    source_endpoint_b = _contact_vector(
        posed_proxy.get("b"), "semantic render/collision selected posed proxy endpoint b"
    )
    source_segment = [right - left for left, right in zip(source_endpoint_a, source_endpoint_b)]
    source_segment_length = math.sqrt(sum(component * component for component in source_segment))
    source_radius = _contact_scalar(
        posed_proxy.get("radius"), "semantic render/collision selected posed proxy radius"
    )
    if not math.isfinite(source_segment_length) or source_segment_length <= 1.0e-12 or source_radius <= 0.0:
        raise SmokeError("semantic render/collision selected posed proxy geometry is degenerate")

    selected_capsule = coherence["selected_capsule"]
    if not isinstance(selected_capsule, dict) or set(selected_capsule) != {
        "target_index",
        "source_bone_id",
        "source_shape_index",
        "runtime_shape_index",
        "source_lineage",
        "source_geometry_binding",
    }:
        raise SmokeError("Godot semantic render/collision selected capsule lineage is incomplete or aliased")
    expected_selected = {
        "target_index": 1,
        "source_bone_id": response_participant.get("source_bone_id"),
        "source_shape_index": response_participant.get("source_proxy_index"),
        "runtime_shape_index": response_participant.get("runtime_shape_index"),
        "source_lineage": "semantic_contact.participants[1].posed_proxy",
        "source_geometry_binding": "radius-and-central-segment-length-only",
    }
    if not _exact_json_equal(selected_capsule, expected_selected) or (
        selected_capsule["source_bone_id"] != deformation_evidence.get("source_bone_id")
        or selected_capsule["source_shape_index"] != deformation_evidence.get("source_shape_index")
        or selected_capsule["runtime_shape_index"] != deformation_evidence.get("runtime_shape_index")
    ):
        raise SmokeError("Godot semantic render/collision selected capsule lineage is mismatched")

    surface = deformation_evidence.get("surface")
    drive = deformation_evidence.get("drive")
    if not isinstance(surface, dict) or not isinstance(drive, dict):
        raise SmokeError("Godot semantic render/collision coherence deformation source is incomplete")
    surface_radius = _contact_scalar(
        surface.get("baseline_radius"), "semantic render/collision deformation baseline radius"
    )
    surface_length = _contact_scalar(
        surface.get("baseline_length"), "semantic render/collision deformation baseline length"
    )
    if (
        abs(source_radius - surface_radius) > TOLERANCE
        or abs(source_segment_length - surface_length) > TOLERANCE
    ):
        raise SmokeError("Godot semantic render/collision coherence source geometry is mismatched")
    falloff_weights = drive.get("falloff_weights")
    if (
        not isinstance(falloff_weights, list)
        or len(falloff_weights) != RENDER_COLLISION_COHERENCE_VERTEX_COUNT
        or any(not _finite_number(weight) or float(weight) < 0.0 or float(weight) > 1.0 for weight in falloff_weights)
        or not any(float(weight) == 0.0 for weight in falloff_weights)
    ):
        raise SmokeError("Godot semantic render/collision coherence falloff source is incomplete")

    states = coherence["states"]
    if (
        not isinstance(states, list)
        or len(states) != len(RENDER_COLLISION_COHERENCE_STATE_ORDER)
    ):
        raise SmokeError("Godot semantic render/collision coherence states are incomplete or not an ordered list")
    state_values: dict[str, dict[str, Any]] = {}
    state_geometry: dict[str, tuple[list[float], list[float], float, float, list[float]]] = {}
    capsule_to_body_reference: list[float] | None = None
    identity = _render_identity_matrix()
    for state_index, (expected_state, expected_phase) in enumerate(zip(
        RENDER_COLLISION_COHERENCE_STATE_ORDER, ("setup", "contact", "contact", "exit")
    )):
        state = states[state_index]
        if not isinstance(state, dict) or set(state) != RENDER_COLLISION_COHERENCE_STATE_KEYS:
            raise SmokeError(f"Godot semantic render/collision {expected_state} state has unexpected or missing fields")
        if state["state"] != expected_state or state["phase"] != expected_phase or type(state["contact"]) is not bool:
            raise SmokeError(f"Godot semantic render/collision {expected_state} state identity is invalid")
        tick = state["tick"]
        sample_index = state["contact_sample_index"]
        if type(tick) is not int or tick < 0 or tick > CONTACT_TOTAL_TICKS or type(sample_index) is not int:
            raise SmokeError(f"Godot semantic render/collision {expected_state} timing is invalid")
        if expected_state in ("neutral", "recovery"):
            if state["contact"] or sample_index != -1:
                raise SmokeError(f"Godot semantic render/collision {expected_state} incorrectly reports contact")
        elif not state["contact"] or sample_index < 0:
            raise SmokeError(f"Godot semantic render/collision {expected_state} contact attribution is invalid")

        response_transform = _validate_render_matrix(
            state["response_body_to_world"],
            f"semantic render/collision {expected_state}.response_body_to_world",
        )
        capsule_transform = _validate_render_matrix(
            state["capsule_to_body"],
            f"semantic render/collision {expected_state}.capsule_to_body",
        )
        sleeve_transform = _validate_render_matrix(
            state["sleeve_to_body"],
            f"semantic render/collision {expected_state}.sleeve_to_body",
        )
        _render_matrix_close(sleeve_transform, identity, f"semantic render/collision {expected_state}.sleeve_to_body")
        if capsule_to_body_reference is None:
            capsule_to_body_reference = capsule_transform
        else:
            _render_matrix_close(
                capsule_transform,
                capsule_to_body_reference,
                f"semantic render/collision {expected_state}.capsule_to_body",
            )

        capsule = state["capsule"]
        if not isinstance(capsule, dict) or set(capsule) != RENDER_COLLISION_COHERENCE_CAPSULE_KEYS:
            raise SmokeError(f"Godot semantic render/collision {expected_state} capsule is incomplete or aliased")
        endpoint_a = _contact_vector(capsule["endpoint_a"], f"semantic render/collision {expected_state}.capsule.endpoint_a")
        endpoint_b = _contact_vector(capsule["endpoint_b"], f"semantic render/collision {expected_state}.capsule.endpoint_b")
        radius = _contact_scalar(capsule["radius"], f"semantic render/collision {expected_state}.capsule.radius")
        height = _contact_scalar(capsule["height"], f"semantic render/collision {expected_state}.capsule.height")
        central_length = height - 2.0 * radius
        if radius <= 0.0 or height <= 0.0 or not math.isfinite(central_length) or central_length <= 1.0e-12:
            raise SmokeError(f"Godot semantic render/collision {expected_state} capsule dimensions are degenerate")
        endpoint_distance = math.sqrt(sum((right - left) ** 2 for left, right in zip(endpoint_a, endpoint_b)))
        if not math.isfinite(endpoint_distance) or endpoint_distance <= 1.0e-12:
            raise SmokeError(f"Godot semantic render/collision {expected_state} capsule endpoints are degenerate")
        if (
            abs(radius - source_radius) > TOLERANCE
            or abs(central_length - source_segment_length) > TOLERANCE
            or abs(endpoint_distance - central_length) > TOLERANCE
        ):
            raise SmokeError(
                f"Godot semantic render/collision {expected_state} capsule radius or central segment length is mismatched"
            )
        expected_endpoint_a = _render_matrix_point(capsule_transform, [0.0, -0.5 * central_length, 0.0])
        expected_endpoint_b = _render_matrix_point(capsule_transform, [0.0, 0.5 * central_length, 0.0])
        if any(abs(left - right) > TOLERANCE for left, right in zip(endpoint_a, expected_endpoint_a)) or any(
            abs(left - right) > TOLERANCE for left, right in zip(endpoint_b, expected_endpoint_b)
        ):
            raise SmokeError(
                f"Godot semantic render/collision {expected_state} capsule endpoints are not reconstructed from capsule_to_body"
            )

        vertices = state["vertices"]
        if not isinstance(vertices, list) or len(vertices) != RENDER_COLLISION_COHERENCE_VERTEX_COUNT:
            raise SmokeError(f"Godot semantic render/collision {expected_state} vertices are incomplete or aggregate-only")
        parsed_vertices = [
            _contact_vector(vertex, f"semantic render/collision {expected_state} vertex {vertex_index}")
            for vertex_index, vertex in enumerate(vertices)
        ]
        metrics = state["metrics"]
        if not isinstance(metrics, dict) or set(metrics) != RENDER_COLLISION_COHERENCE_METRIC_KEYS:
            raise SmokeError(f"Godot semantic render/collision {expected_state} metrics are incomplete or aliased")
        actual_metrics = _render_collision_metrics(
            parsed_vertices,
            endpoint_a,
            endpoint_b,
            radius,
            falloff_weights,
            f"semantic render/collision {expected_state}",
        )
        for metric_name, actual in actual_metrics.items():
            reported = _contact_scalar(metrics[metric_name], f"semantic render/collision {expected_state}.{metric_name}")
            if reported < 0.0 or abs(reported - actual) > TOLERANCE:
                raise SmokeError(
                    f"Godot semantic render/collision {expected_state}.{metric_name} does not match reconstructed clearance"
                )
        state_values[expected_state] = state
        state_geometry[expected_state] = (endpoint_a, endpoint_b, radius, height, response_transform)

    first_positive_sample = _render_first_positive_contact_sample(contact_evidence)
    if (
        (first_positive_sample["tick"], first_positive_sample["contact_index"])
        != (state_values["contact_onset"]["tick"], state_values["contact_onset"]["contact_sample_index"])
    ):
        raise SmokeError("Godot semantic render/collision onset is not the first validated positive contact sample")
    peak_tick = drive.get("peak_tick")
    peak_sample_index = drive.get("contact_sample_index")
    if (
        type(peak_tick) is not int
        or type(peak_sample_index) is not int
        or (peak_tick, peak_sample_index)
        != (state_values["peak"]["tick"], state_values["peak"]["contact_sample_index"])
        or (peak_tick, peak_sample_index)
        != (strongest_contact_sample.get("tick"), strongest_contact_sample.get("contact_index"))
    ):
        raise SmokeError("Godot semantic render/collision peak is not tied to the strongest deformation contact sample")
    if state_values["neutral"]["tick"] != 0 or state_values["recovery"]["tick"] != DEFORMATION_RECOVERY_TICK:
        raise SmokeError("Godot semantic render/collision neutral or recovery tick is invalid")

    snapshots = contact_evidence.get("response", {}).get("snapshots", {})
    if not isinstance(snapshots, dict) or set(snapshots) != {"initial", "onset", "contact", "final"}:
        raise SmokeError("Godot semantic render/collision response snapshots are missing")
    initial_transform = _validate_render_matrix(
        snapshots["initial"].get("transform"), "semantic render/collision initial response transform"
    )
    onset_transform = _validate_render_matrix(
        snapshots["onset"].get("transform"), "semantic render/collision onset response transform"
    )
    contact_transform = _validate_render_matrix(
        snapshots["contact"].get("transform"), "semantic render/collision contact response transform"
    )
    final_transform = _validate_render_matrix(
        snapshots["final"].get("transform"), "semantic render/collision final response transform"
    )
    peak_transform = _validate_render_matrix(
        drive.get("sample_response_transform"), "semantic render/collision peak response transform"
    )
    _render_matrix_close(
        state_geometry["neutral"][4], initial_transform, "semantic render/collision neutral response_body_to_world"
    )
    _render_matrix_close(
        state_geometry["contact_onset"][4], onset_transform, "semantic render/collision onset response_body_to_world"
    )
    _render_matrix_close(
        state_geometry["peak"][4], peak_transform, "semantic render/collision peak response_body_to_world"
    )
    _render_matrix_close(peak_transform, contact_transform, "semantic render/collision peak contact snapshot transform")
    _render_matrix_close(
        state_geometry["recovery"][4], final_transform, "semantic render/collision recovery response_body_to_world"
    )

    deformation_states = deformation_evidence.get("states")
    if not isinstance(deformation_states, dict):
        raise SmokeError("Godot semantic render/collision deformation state cross-link is missing")
    for coherence_state, deformation_state in (
        ("neutral", "reference"),
        ("peak", "peak"),
        ("recovery", "recovered"),
    ):
        expected_vertices = deformation_states.get(deformation_state, {}).get("vertices")
        actual_vertices = state_values[coherence_state]["vertices"]
        if not isinstance(expected_vertices, list) or len(expected_vertices) != len(actual_vertices):
            raise SmokeError("Godot semantic render/collision vertex cross-link is incomplete")
        if any(
            abs(float(actual) - float(expected)) > TOLERANCE
            for actual_vertex, expected_vertex in zip(actual_vertices, expected_vertices)
            for actual, expected in zip(actual_vertex, expected_vertex)
        ):
            raise SmokeError(f"Godot semantic render/collision {coherence_state} vertices disagree with deformation evidence")
    if state_values["recovery"]["vertices"] != state_values["neutral"]["vertices"]:
        raise SmokeError("Godot semantic render/collision recovery is not exact")

    neutral_metrics = state_values["neutral"]["metrics"]
    recovery_metrics = state_values["recovery"]["metrics"]
    if (
        float(neutral_metrics["maximum_absolute_side_clearance"]) > TOLERANCE
        or float(recovery_metrics["maximum_absolute_side_clearance"]) > TOLERANCE
    ):
        raise SmokeError("Godot semantic render/collision neutral or recovery side clearance exceeds tolerance")
    peak_metrics = state_values["peak"]["metrics"]
    absolute_peak_depth = _contact_scalar(
        drive.get("absolute_peak_depth"), "semantic render/collision absolute peak depth"
    )
    if (
        float(peak_metrics["maximum_inward_penetration"]) <= 0.0
        or float(peak_metrics["maximum_inward_penetration"]) > absolute_peak_depth + TOLERANCE
        or float(peak_metrics["maximum_outward_clearance"]) > TOLERANCE
        or float(peak_metrics["outside_falloff_max_penetration"]) > TOLERANCE
    ):
        raise SmokeError("Godot semantic render/collision peak clearance is outside the bounded deformation envelope")

    drift = coherence["collision_geometry_drift"]
    if not isinstance(drift, dict) or set(drift) != RENDER_COLLISION_COHERENCE_DRIFT_KEYS:
        raise SmokeError("Godot semantic render/collision geometry drift is incomplete or aliased")
    if drift["reference_state"] != "neutral":
        raise SmokeError("Godot semantic render/collision geometry drift reference is invalid")
    neutral_endpoint_a, neutral_endpoint_b, neutral_radius, _neutral_height, _ = state_geometry["neutral"]
    actual_drift = {
        "max_endpoint_a_drift": max(
            math.sqrt(sum((state_geometry[label][0][axis] - neutral_endpoint_a[axis]) ** 2 for axis in range(3)))
            for label in RENDER_COLLISION_COHERENCE_STATE_ORDER
        ),
        "max_endpoint_b_drift": max(
            math.sqrt(sum((state_geometry[label][1][axis] - neutral_endpoint_b[axis]) ** 2 for axis in range(3)))
            for label in RENDER_COLLISION_COHERENCE_STATE_ORDER
        ),
        "max_radius_drift": max(
            abs(state_geometry[label][2] - neutral_radius) for label in RENDER_COLLISION_COHERENCE_STATE_ORDER
        ),
    }
    actual_drift["maximum_geometry_drift"] = max(actual_drift.values())
    for drift_name, actual in actual_drift.items():
        reported = _contact_scalar(drift[drift_name], f"semantic render/collision {drift_name}")
        if reported < 0.0 or abs(reported - actual) > TOLERANCE:
            raise SmokeError(f"Godot semantic render/collision {drift_name} does not match state geometry")
    if actual_drift["maximum_geometry_drift"] > TOLERANCE:
        raise SmokeError("Godot semantic render/collision rigid capsule geometry drift exceeds tolerance")


def _validate_deformation_captures(
    evidence: dict[str, Any],
    staged_captures: dict[str, bytes],
) -> None:
    if set(staged_captures) != set(DEFORMATION_CAPTURE_NAMES):
        raise SmokeError("staged deformation captures are incomplete or unexpected")
    captures = evidence.get("captures")
    if not isinstance(captures, list) or len(captures) != len(DEFORMATION_CAPTURE_NAMES):
        raise SmokeError("Godot semantic deformation capture records are incomplete or reordered")
    capture_keys = {"label", "file_name", "width", "height", "sha256", "byte_count_decimal"}
    decoded_captures: dict[str, bytes] = {}
    for index, (record, label, file_name) in enumerate(
        zip(captures, DEFORMATION_CAPTURE_LABELS, DEFORMATION_CAPTURE_NAMES)
    ):
        if not isinstance(record, dict) or set(record) != capture_keys:
            raise SmokeError(f"Godot semantic deformation capture record {index} is incomplete")
        if (
            record["label"] != label
            or record["file_name"] != file_name
            or type(record["width"]) is not int
            or record["width"] != DEFORMATION_CAPTURE_WIDTH
            or type(record["height"]) is not int
            or record["height"] != DEFORMATION_CAPTURE_HEIGHT
        ):
            raise SmokeError(f"Godot semantic deformation capture record {index} identity or dimensions are invalid")
        data = staged_captures[file_name]
        decoded = _decode_deformation_png(data, file_name)
        decoded_captures[file_name] = decoded
        metrics = _decoded_capture_metrics(decoded)
        if (
            metrics["unique_rgba_pixels"] < DEFORMATION_CAPTURE_MIN_UNIQUE_RGBA_PIXELS
            or metrics["non_dominant_pixels"] < DEFORMATION_CAPTURE_MIN_NON_DOMINANT_PIXELS
        ):
            raise SmokeError(
                f"deformation capture {file_name} is blank or uniform by decoded-pixel integrity checks: "
                f"observed_unique_rgba_pixels={metrics['unique_rgba_pixels']} "
                f"observed_non_dominant_pixels={metrics['non_dominant_pixels']} "
                f"required_unique_rgba_pixels>={DEFORMATION_CAPTURE_MIN_UNIQUE_RGBA_PIXELS} "
                f"required_non_dominant_pixels>={DEFORMATION_CAPTURE_MIN_NON_DOMINANT_PIXELS}"
            )
        expected_sha = hashlib.sha256(data).hexdigest()
        expected_bytes = str(len(data))
        if (
            not isinstance(record["sha256"], str)
            or len(record["sha256"]) != 64
            or any(character not in "0123456789abcdef" for character in record["sha256"])
            or record["sha256"] != expected_sha
            or not isinstance(record["byte_count_decimal"], str)
            or record["byte_count_decimal"] != expected_bytes
            or not record["byte_count_decimal"].isascii()
            or not record["byte_count_decimal"].isdigit()
            or record["byte_count_decimal"].startswith("0")
        ):
            raise SmokeError(f"Godot semantic deformation capture record {index} does not match staged bytes")

    reference = decoded_captures["reference.png"]
    recovered = decoded_captures["recovered.png"]
    if reference != recovered:
        recovery_difference = _decoded_capture_difference(reference, recovered)
        raise SmokeError(
            "deformation recovered capture does not exactly equal the decoded reference pixels: "
            f"observed_changed_pixels={recovery_difference['changed_pixels']} "
            f"observed_total_abs_channel_delta={recovery_difference['total_abs_channel_delta']} "
            f"observed_max_channel_delta={recovery_difference['max_channel_delta']}"
        )

    peak_difference = _decoded_capture_difference(reference, decoded_captures["peak.png"])
    if (
        peak_difference["changed_pixels"] < DEFORMATION_CAPTURE_MIN_CHANGED_PIXELS
        or peak_difference["total_abs_channel_delta"] < DEFORMATION_CAPTURE_MIN_TOTAL_ABS_CHANNEL_DELTA
        or peak_difference["changed_pixel_fraction"] > DEFORMATION_CAPTURE_MAX_CHANGED_PIXEL_FRACTION
    ):
        raise SmokeError(
            "deformation peak capture is not a bounded meaningful decoded-pixel distinction from reference: "
            f"observed_changed_pixels={peak_difference['changed_pixels']} "
            f"observed_changed_pixel_fraction={peak_difference['changed_pixel_fraction']:.9g} "
            f"observed_total_abs_channel_delta={peak_difference['total_abs_channel_delta']} "
            f"observed_max_channel_delta={peak_difference['max_channel_delta']} "
            f"required_changed_pixels>={DEFORMATION_CAPTURE_MIN_CHANGED_PIXELS} "
            f"required_total_abs_channel_delta>={DEFORMATION_CAPTURE_MIN_TOTAL_ABS_CHANNEL_DELTA} "
            f"required_changed_pixel_fraction<={DEFORMATION_CAPTURE_MAX_CHANGED_PIXEL_FRACTION}"
        )


def _validate_report(
    report: Any,
    payload: dict[str, Any],
    profile_ids: tuple[str, str],
    carrier_identity: dict[str, Any] | None = None,
    carrier_avatar_records: list[dict[str, str]] | None = None,
    semantic_pose_command: dict[str, Any] | None = None,
    command_identity: dict[str, Any] | None = None,
    projection: dict[str, Any] | None = None,
    projection_identity: dict[str, Any] | None = None,
    semantic_contact_command: dict[str, Any] | None = None,
    contact_command_identity: dict[str, Any] | None = None,
    deformation_capture_bytes: dict[str, bytes] | None = None,
    runtime_measurement_mode: str | None = None,
    validated_ck_package: dict[str, Any] | None = None,
) -> None:
    if not isinstance(report, dict):
        raise SmokeError("Godot skeletal-pose report is not a JSON object")
    _validate_finite_report_json(report)
    _validate_carrier_expectations(carrier_identity, carrier_avatar_records, payload, profile_ids)
    if (projection is None) != (projection_identity is None):
        raise SmokeError("CK projection and projection identity must be supplied together")
    if projection is None:
        if "validated_ck_projection" in report:
            raise SmokeError("no-projection Godot report contains unexpected CK projection identity")
    elif report.get("validated_ck_projection") != projection_identity:
        raise SmokeError("Godot report CK projection identity does not match the validated projection")
    if report.get("schema") != REPORT_SCHEMA or report.get("status") != "success":
        raise SmokeError("Godot skeletal-pose report schema or status is invalid")
    deformation_mode = deformation_capture_bytes is not None
    if runtime_measurement_mode is not None:
        runtime_measurement_mode = _validate_runtime_measurement_mode(runtime_measurement_mode)
        if semantic_contact_command is None:
            raise SmokeError("runtime measurement requires the full semantic-contact predecessor set")
        if runtime_measurement_mode == "cpu_deformation" and not deformation_mode:
            raise SmokeError("cpu_deformation runtime measurement requires deformation captures")
        if runtime_measurement_mode == "rigid_contact_only" and deformation_mode:
            raise SmokeError("rigid_contact_only runtime measurement cannot include deformation captures")
    elif "runtime_measurement" in report:
        raise SmokeError("Godot report contains runtime_measurement without a requested runtime measurement mode")
    if "runtime_evaluation" in report:
        raise SmokeError("Godot report contains unexpected runtime_evaluation publication")
    if deformation_mode and semantic_contact_command is None:
        raise SmokeError("semantic deformation requires the full semantic-contact predecessor set")
    expected_report_boundary = (
        DEFORMATION_REPORT_BOUNDARY
        if deformation_mode
        else CONTACT_REPORT_BOUNDARY
        if semantic_contact_command is not None
        else REPORT_BOUNDARY
    )
    if report.get("boundary") != expected_report_boundary:
        raise SmokeError("Godot skeletal-pose report boundary is invalid")
    expected_claims = (
        DEFORMATION_REPORT_CLAIMS
        if deformation_mode
        else CONTACT_REPORT_CLAIMS
        if semantic_contact_command is not None
        else REPORT_CLAIMS
    )
    if report.get("claims") != expected_claims:
        raise SmokeError("Godot skeletal-pose report contains an unexpected claim")
    expected_scope_flags = (
        DEFORMATION_REPORT_FLAGS
        if deformation_mode
        else CONTACT_REPORT_FLAGS
        if semantic_contact_command is not None
        else REPORT_FLAGS
    )
    scope_flags = report.get("scope_flags")
    if (
        not isinstance(scope_flags, dict)
        or scope_flags != expected_scope_flags
        or any(type(scope_flags.get(key)) is not bool for key in expected_scope_flags)
    ):
        raise SmokeError("Godot skeletal-pose report scope flags are not fail-closed")
    if report.get("godot_version") != EXPECTED_GODOT_VERSION:
        raise SmokeError(f"Godot report version is not exact: {report.get('godot_version')!r}")
    if report.get("godot_engine_version_string") != EXPECTED_GODOT_ENGINE_VERSION_STRING:
        raise SmokeError(f"Godot runtime version string is not exact: {report.get('godot_engine_version_string')!r}")
    if report.get("profile_ids") != list(profile_ids):
        raise SmokeError("Godot report profile IDs do not match the preflight selection")
    expected_hashes = {profile["profile_id"]: profile["candidate_profile_sha256"] for profile in payload["profiles"]}
    if report.get("candidate_profile_sha256") != expected_hashes:
        raise SmokeError("Godot report candidate identity hashes do not match the validated projection")
    if report.get("validated_gallery") != _expected_gallery_identity(payload):
        raise SmokeError("Godot report validated-gallery identity does not match the projection")
    if report.get("artifact_hash_identities") != _expected_artifact_identities(payload):
        raise SmokeError("Godot report artifact identities do not match the validated projection")
    _validate_carrier_report_identity(
        report.get("validated_carrier"),
        carrier_identity,
        "validated_carrier" in report,
    )
    _validate_carrier_avatar_bindings(
        report.get("carrier_avatar_bindings"),
        carrier_avatar_records,
        "carrier_avatar_bindings" in report,
    )
    _validate_ck_package_report_identity(
        report.get("validated_ck_package"),
        validated_ck_package,
        "validated_ck_package" in report,
    )
    if semantic_pose_command is None and any(
        key in report
        for key in ("semantic_pose_command_identity", "semantic_pose_targets", "semantic_pose_frame")
    ):
        raise SmokeError("no-command Godot report contains unexpected semantic pose command evidence")
    _validate_command_expectations(
        report.get("semantic_pose_command_identity"),
        report.get("semantic_pose_targets"),
        report.get("semantic_pose_frame"),
        semantic_pose_command,
        command_identity,
        payload,
        carrier_avatar_records,
    )
    contact_report_keys = {
        "semantic_contact",
        "semantic_deformation",
        "semantic_render_collision_coherence",
        *CONTACT_REPORT_ALIAS_KEYS,
        *DEFORMATION_REPORT_ALIAS_KEYS,
        *RENDER_COLLISION_COHERENCE_ALIAS_KEYS,
    }
    if semantic_contact_command is None:
        if contact_report_keys.intersection(report):
            raise SmokeError("no-contact Godot report contains unexpected semantic contact evidence")
    else:
        if contact_command_identity is None:
            raise SmokeError("semantic contact command identity expectation is missing")
        strongest_contact_sample = _validate_contact_report(report, semantic_contact_command, contact_command_identity)
        if deformation_mode:
            _validate_render_collision_coherence(report, strongest_contact_sample)
            _validate_deformation_report(report, strongest_contact_sample)
            if not isinstance(deformation_capture_bytes, dict):
                raise SmokeError("semantic deformation staged captures are missing")
            _validate_deformation_captures(report["semantic_deformation"], deformation_capture_bytes)
        elif (
            "semantic_deformation" in report
            or DEFORMATION_REPORT_ALIAS_KEYS.intersection(report)
            or "semantic_render_collision_coherence" in report
            or RENDER_COLLISION_COHERENCE_ALIAS_KEYS.intersection(report)
        ):
            raise SmokeError("contact-only Godot report contains unexpected semantic deformation or render/collision evidence")
        if runtime_measurement_mode is not None:
            _validate_runtime_measurement(
                report.get("runtime_measurement"),
                runtime_measurement_mode,
                report,
            )
    if report.get("coordinate_rule") != {
        "kind": "disposable_host_local_identity",
        "mapping": "CK XYZ -> Godot XYZ: x->x, y->y, z->z",
        "scope": expected_report_boundary,
        "profile_translations": [list(value) for value in EXPECTED_TRANSLATIONS],
    }:
        raise SmokeError("Godot skeletal-pose report coordinate rule is invalid")
    expected_pose_binding = {
        "pose_id": payload["pose_id"],
        "pose_sha256": payload["pose_sha256"],
        "path": "injected-semantic-pose-command" if semantic_pose_command is not None else "structural_embodiment_shared_pose.json",
        "rule_count": BONE_COUNT,
        "rules_validated": True,
        "applied_to_skeleton3d": True,
        "ik": False,
        "contact": semantic_contact_command is not None,
    }
    pose_binding = report.get("pose_binding")
    if (
        not isinstance(pose_binding, dict)
        or pose_binding != expected_pose_binding
        or any(
            type(pose_binding.get(key)) is not bool
            for key in ("rules_validated", "applied_to_skeleton3d", "ik", "contact")
        )
    ):
        raise SmokeError("Godot skeletal-pose report pose binding evidence is invalid")

    actual_profiles = report.get("profiles")
    if not isinstance(actual_profiles, list) or any(not isinstance(item, dict) for item in actual_profiles):
        raise SmokeError("Godot skeletal-pose profile records are incomplete or reordered")
    if [item.get("profile_id") for item in actual_profiles] != list(profile_ids):
        raise SmokeError("Godot skeletal-pose profile records are incomplete or reordered")
    for index, (actual, expected) in enumerate(zip(actual_profiles, payload["profiles"])):
        profile_id = profile_ids[index]
        metrics = expected["metrics"]
        if metrics["bone_count"] != BONE_COUNT or metrics["proxy_count"] != PROXY_COUNT:
            raise SmokeError(f"validated gallery profile {profile_id} does not establish the exact 18/18 contract")
        if actual.get("candidate_profile_sha256") != expected["candidate_profile_sha256"]:
            raise SmokeError(f"Godot report profile {profile_id} identity differs from the validated projection")
        if projection is None:
            if "ck_projection_binding" in actual:
                raise SmokeError("no-projection Godot report contains unexpected CK projection binding")
        elif actual.get("ck_projection_binding") != _projection_bindings(projection)[index]:
            raise SmokeError(f"Godot report profile {profile_id} CK projection binding is invalid")
        if not neutral_smoke._values_close(actual.get("metrics"), metrics):
            raise SmokeError(f"Godot report profile {profile_id} metrics differ from the validated projection")
        if actual.get("profile_translation") != list(EXPECTED_TRANSLATIONS[index]):
            raise SmokeError(f"Godot report profile {profile_id} translation is not fixed host-only separation")
        expected_counts = {
            "neutral_vertex_count": metrics["neutral_vertex_count"],
            "posed_vertex_count": metrics["posed_vertex_count"],
            "face_count": metrics["face_count"],
            "bone_count": BONE_COUNT,
            "proxy_count": PROXY_COUNT,
            "weight_vertex_count": metrics["neutral_vertex_count"],
        }
        counts = actual.get("counts")
        if not isinstance(counts, dict):
            raise SmokeError(f"Godot report profile {profile_id} structural counts are invalid")
        neutral_smoke._validate_exact_count_map(
            counts,
            tuple(expected_counts) + ("influence_count",),
            f"Godot report profile {profile_id} counts",
        )
        if any(counts[key] != value for key, value in expected_counts.items()) or counts["influence_count"] < metrics["neutral_vertex_count"]:
            raise SmokeError(f"Godot report profile {profile_id} structural counts are invalid")
        for bounds_key, expected_bounds in (("neutral_mesh_aabb", metrics["neutral_bounds"]), ("posed_mesh_aabb", metrics["posed_bounds"])):
            if not _finite_bounds(actual.get(bounds_key)) or not neutral_smoke._bounds_close(
                actual.get(bounds_key), expected_bounds, TOLERANCE
            ):
                raise SmokeError(f"Godot report profile {profile_id} {bounds_key} differs from published metrics")
        if not _finite_bounds(actual.get("posed_proxy_aabb")):
            raise SmokeError(f"Godot report profile {profile_id} posed proxy bounds are invalid")
        node_counts = actual.get("node_counts")
        if not isinstance(node_counts, dict):
            raise SmokeError(f"Godot report profile {profile_id} node counts are invalid")
        neutral_smoke._validate_exact_count_map(
            node_counts,
            ("profile_root", "skeleton_3d", "mesh_instance_3d", "static_body_3d", "collision_shape_3d", "total_profile_nodes"),
            f"Godot report profile {profile_id} node_counts",
        )
        if node_counts != {
            "profile_root": 1,
            "skeleton_3d": 1,
            "mesh_instance_3d": 1,
            "static_body_3d": 1,
            "collision_shape_3d": PROXY_COUNT,
            "total_profile_nodes": 4 + PROXY_COUNT,
        }:
            raise SmokeError(f"Godot report profile {profile_id} node counts are invalid")
        _validate_binding(actual.get("binding"), profile_id)
        if semantic_pose_command is None:
            if "semantic_pose_injection" in actual:
                raise SmokeError("no-command Godot report contains unexpected per-avatar semantic pose evidence")
        else:
            injection = actual.get("semantic_pose_injection")
            _validate_command_injection(
                injection,
                carrier_avatar_records[index],
                semantic_pose_command,
                profile_id,
            )
    first_proxy_max = actual_profiles[0]["posed_proxy_aabb"]["max"][0] + EXPECTED_TRANSLATIONS[0][0]
    second_proxy_min = actual_profiles[1]["posed_proxy_aabb"]["min"][0] + EXPECTED_TRANSLATIONS[1][0]
    if first_proxy_max >= second_proxy_min:
        raise SmokeError("Godot report posed proxy bounds are not separated by fixed host-only translations")
    neutral_smoke._reject_absolute_paths(report)


def _finite_bounds(value: Any) -> bool:
    if not isinstance(value, dict) or set(value) != {"min", "max"}:
        return False
    return all(
        isinstance(vector, list)
        and len(vector) == 3
        and all(_finite_number(axis) for axis in vector)
        for vector in value.values()
    )


def _launch_godot(
    gallery: Path,
    profile_ids: tuple[str, str],
    payload: dict[str, Any],
    carrier_identity: dict[str, Any] | None = None,
    carrier_avatar_records: list[dict[str, str]] | None = None,
    semantic_pose_command: dict[str, Any] | None = None,
    command_identity: dict[str, Any] | None = None,
    semantic_payload: dict[str, Any] | None = None,
    projection: dict[str, Any] | None = None,
    projection_identity: dict[str, Any] | None = None,
    semantic_contact_command: dict[str, Any] | None = None,
    contact_command_identity: dict[str, Any] | None = None,
    projection_cli_path: Path | None = None,
    *,
    package_path: Path | None = None,
    package_manifest: dict[str, Any] | None = None,
    deformation_capture: bool = False,
    deformation_capture_sink: Any | None = None,
    runtime_measurement_mode: str | None = None,
) -> tuple[str, str, int, dict[str, Any] | None]:
    """Launch with a real renderer; headless mode exposes dummy rendering RIDs."""
    if runtime_measurement_mode is not None:
        runtime_measurement_mode = _validate_runtime_measurement_mode(runtime_measurement_mode)
        if semantic_contact_command is None:
            raise SmokeError("runtime measurement mode requires semantic contact")
        if runtime_measurement_mode == "cpu_deformation" and not deformation_capture:
            raise SmokeError("cpu_deformation runtime measurement requires deformation capture mode")
        if runtime_measurement_mode == "rigid_contact_only" and deformation_capture:
            raise SmokeError("rigid_contact_only runtime measurement cannot use deformation capture mode")
    if os.environ.get(VISIBLE_GODOT_OPT_IN) != "1":
        raise SmokeError(
            f"visible X11 Godot launch is disabled; set {VISIBLE_GODOT_OPT_IN}=1 "
            "only for an attended run"
        )
    if deformation_capture and (
        semantic_contact_command is None
        or deformation_capture_sink is None
        or not callable(deformation_capture_sink)
    ):
        raise SmokeError("deformation capture mode requires semantic contact and a capture sink")
    if package_path is not None and package_manifest is None:
        raise SmokeError("CK package transport requires its validated full manifest")
    if package_manifest is not None and package_path is None:
        raise SmokeError("CK package manifest transport requires its package root")
    if package_path is not None and (
        carrier_identity is None
        or projection is None
        or projection_identity is None
        or projection_cli_path is None
        or semantic_pose_command is None
        or command_identity is None
        or semantic_payload is None
    ):
        raise SmokeError(
            "package transport requires validated carrier, CK projection, explicit Rust CLI, and semantic pose command"
        )
    package_manifest_json: str | None = None
    if package_path is not None:
        package_path = Path(package_path)
        if not package_path.is_absolute():
            raise SmokeError("CK package root must be an absolute path")
        package_module = _load_package_module()
        try:
            package_manifest_json = package_module._canonical_json(package_manifest).decode("utf-8").removesuffix("\n")
        except (AttributeError, UnicodeDecodeError, TypeError, ValueError) as exc:
            raise SmokeError(f"CK package manifest cannot be encoded for Godot transport: {exc}") from exc
        if not package_manifest_json:
            raise SmokeError("CK package manifest transport is empty")
    for required in (neutral_smoke.PROJECT_FILE, GODOT_SCRIPT, neutral_smoke.LAUNCHER):
        if not required.is_file():
            raise SmokeError(f"required Godot skeletal-pose file is unavailable: {required}")
    if not os.access(neutral_smoke.LAUNCHER, os.X_OK):
        raise SmokeError(f"pinned Godot launcher is not executable: {neutral_smoke.LAUNCHER}")
    with tempfile.TemporaryDirectory(prefix="ck-godot-skeletal-pose-smoke-") as temporary:
        isolated_root = Path(temporary) / "isolated"
        isolated_paths = {
            "HOME": isolated_root / "home",
            "XDG_CACHE_HOME": isolated_root / "cache",
            "XDG_CONFIG_HOME": isolated_root / "config",
            "XDG_DATA_HOME": isolated_root / "data",
            "XDG_STATE_HOME": isolated_root / "state",
            "TMPDIR": isolated_root / "tmp",
            "TMP": isolated_root / "tmp",
            "TEMP": isolated_root / "tmp",
            "XDG_RUNTIME_DIR": isolated_root / "runtime",
        }
        for path in set(isolated_paths.values()):
            path.mkdir(parents=True, exist_ok=True)
        pinned_binary = neutral_smoke._resolve_pinned_binary()
        project = Path(temporary) / "project.godot"
        script_path = Path(temporary) / GODOT_SCRIPT.name
        raw_report_path = Path(temporary) / "godot-report.json"
        raw_deformation_capture_path = Path(temporary) / "deformation-captures"
        staged_package_path: Path | None = None
        if deformation_capture:
            raw_deformation_capture_path.mkdir()
        shutil.copyfile(neutral_smoke.PROJECT_FILE, project)
        shutil.copyfile(GODOT_SCRIPT, script_path)
        if package_path is not None:
            staged_package_path, staged_manifest = _stage_validated_ck_package(
                package_path,
                package_manifest,
                Path(temporary) / "staged-ck-package",
            )
            if not _exact_json_equal(staged_manifest, package_manifest):
                raise SmokeError("staged CK package manifest changed before Godot launch")
        input_transport = (
            [
                "--ck-package-root",
                str(staged_package_path),
                "--ck-package-manifest-json",
                package_manifest_json,
            ]
            if package_path is not None
            else ["--gallery", str(gallery)]
        )
        launch_command = [
            str(neutral_smoke.LAUNCHER),
            "--display-driver",
            "x11",
            "--rendering-method",
            "gl_compatibility",
            *(("--resolution", "512x512") if deformation_capture or runtime_measurement_mode is not None else ()),
            "--audio-driver",
            "Dummy",
            "--path",
            str(Path(temporary)),
            "--script",
            str(script_path),
            "--",
            *input_transport,
            "--profile-id",
            profile_ids[0],
            "--profile-id",
            profile_ids[1],
            "--report",
            str(raw_report_path),
            "--validated-json",
            json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False),
        ]
        if carrier_identity is not None:
            launch_command.extend(
                [
                    "--carrier-identity-json",
                    json.dumps(carrier_identity, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False),
                ]
            )
            if carrier_avatar_records is None:
                raise SmokeError("validated carrier avatar records are missing")
            launch_command.extend(
                [
                    "--carrier-avatar-records-json",
                    json.dumps(
                        carrier_avatar_records,
                        ensure_ascii=True,
                        sort_keys=True,
                        separators=(",", ":"),
                        allow_nan=False,
                    ),
                ]
            )
        elif carrier_avatar_records is not None:
            raise SmokeError("carrier avatar records were supplied without validated carrier identity")
        if semantic_pose_command is not None:
            if carrier_identity is None or carrier_avatar_records is None or command_identity is None or semantic_payload is None:
                raise SmokeError("semantic pose command requires validated carrier and semantic payload")
            command_module = _load_command_module()
            command_json = command_module._canonical_json(semantic_pose_command).decode("utf-8").rstrip("\n")
            identity_json = command_module._canonical_json(command_identity).decode("utf-8").rstrip("\n")
            semantic_json = command_module._canonical_json(semantic_payload).decode("utf-8").rstrip("\n")
            # Keep the injected command and its derived payload/identity separate
            # so Godot cannot fall back to reading the shared-pose file.
            launch_command.extend(
                [
                    "--semantic-pose-command-json",
                    command_json,
                    "--semantic-pose-command-identity-json",
                    identity_json,
                    "--semantic-pose-payload-json",
                    semantic_json,
                ]
            )
        if projection is not None:
            if carrier_identity is None or projection_identity is None:
                raise SmokeError("CK projection requires validated carrier and projection identity")
            projection_module = _load_projection_module()
            projection_json = projection_module._canonical_json(projection).decode("utf-8").removesuffix("\n")
            identity_json = projection_module._canonical_json(projection_identity).decode("utf-8").removesuffix("\n")
            launch_command.extend(
                [
                    "--ck-projection-json",
                    projection_json,
                    "--ck-projection-identity-json",
                    identity_json,
                ]
            )
        elif projection_identity is not None:
            raise SmokeError("CK projection identity was supplied without a validated projection")
        if semantic_contact_command is not None:
            if (
                carrier_identity is None
                or carrier_avatar_records is None
                or semantic_pose_command is None
                or command_identity is None
                or projection is None
                or projection_identity is None
                or projection_cli_path is None
                or contact_command_identity is None
            ):
                raise SmokeError(
                    "semantic contact command requires carrier, CK projection, explicit Rust CLI, and semantic pose command"
                )
            contact_module = _load_contact_command_module()
            contact_json = contact_module._canonical_json(semantic_contact_command).decode("utf-8").rstrip("\n")
            contact_identity_json = contact_module._canonical_json(contact_command_identity).decode("utf-8").rstrip("\n")
            launch_command.extend(
                [
                    "--semantic-contact-command-json",
                    contact_json,
                    "--semantic-contact-command-identity-json",
                    contact_identity_json,
                ]
            )
        elif contact_command_identity is not None:
            raise SmokeError("semantic contact command identity was supplied without a command")
        if deformation_capture:
            launch_command.extend(["--deformation-capture-dir", str(raw_deformation_capture_path)])
        if runtime_measurement_mode is not None:
            launch_command.extend(["--runtime-measurement-mode", runtime_measurement_mode])
        environment = os.environ.copy()
        environment.update({key: str(value) for key, value in isolated_paths.items()})
        environment["CK_GODOT_4_7_2_BINARY"] = str(pinned_binary)
        try:
            completed = subprocess.run(
                launch_command,
                cwd=neutral_smoke.REPOSITORY_ROOT,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
                timeout=neutral_smoke.GODOT_LAUNCH_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            raise SmokeError(
                f"Godot launcher exceeded {neutral_smoke.GODOT_LAUNCH_TIMEOUT_SECONDS}s; "
                f"stdout={exc.stdout!r}; stderr={exc.stderr!r}"
            ) from exc
        except OSError as exc:
            raise SmokeError(f"Godot launcher invocation failed: {type(exc).__name__}: {exc}") from exc
        diagnostic = f"stdout={completed.stdout!r}; stderr={completed.stderr!r}"
        if neutral_smoke._has_godot_error_diagnostics(completed.stdout, completed.stderr):
            raise SmokeError(f"Godot launcher emitted error/leak diagnostics; {diagnostic}")
        if completed.returncode != 0:
            return completed.stdout, completed.stderr, completed.returncode, None
        report = neutral_smoke._read_report(raw_report_path)
        if deformation_capture:
            deformation_capture_sink(_read_deformation_capture_bytes(raw_deformation_capture_path))
        return completed.stdout, completed.stderr, completed.returncode, report


def run_skeletal_pose_smoke(
    gallery: Path,
    profile_ids: tuple[str, str] | list[str] | None,
    report_path: Path,
    carrier_path: Path | None = None,
    command_path: Path | None = None,
    projection_path: Path | None = None,
    projection_cli_path: Path | None = None,
    contact_command_path: Path | None = None,
    deformation_captures_path: Path | None = None,
    runtime_evaluation: bool = False,
    package_path: Path | None = None,
) -> dict[str, Any]:
    report_path = neutral_smoke._validate_report_destination(report_path)
    gallery = Path(gallery)
    if type(runtime_evaluation) is not bool:
        raise SmokeError("runtime_evaluation must be an exact boolean")
    if package_path is not None and any(
        value is None
        for value in (carrier_path, projection_path, projection_cli_path, command_path)
    ):
        raise SmokeError(
            "package mode requires carrier, CK projection, explicit Rust CLI, and semantic pose command"
        )
    if runtime_evaluation and (
        carrier_path is None
        or command_path is None
        or projection_path is None
        or projection_cli_path is None
        or contact_command_path is None
        or deformation_captures_path is None
    ):
        raise SmokeError(
            "runtime evaluation requires the full deformation-capture/contact predecessor set: "
            "carrier, CK projection, explicit Rust CLI, semantic pose command, semantic contact command, "
            "and deformation captures"
        )
    if deformation_captures_path is not None:
        deformation_captures_path = _validate_deformation_capture_destination(Path(deformation_captures_path))
        if (
            carrier_path is None
            or command_path is None
            or projection_path is None
            or projection_cli_path is None
            or contact_command_path is None
        ):
            raise SmokeError(
            "deformation captures require the full semantic-contact predecessor set: carrier, CK projection, explicit Rust CLI, semantic pose command, and semantic contact command"
            )
    carrier_identity = None
    carrier_avatar_records = None
    command = None
    command_identity = None
    semantic_payload = None
    projection = None
    projection_identity_value = None
    package_manifest = None
    validated_ck_package = None
    contact_command = None
    contact_command_identity = None
    staged_deformation_captures: dict[str, bytes] | None = (
        {} if deformation_captures_path is not None else None
    )
    if contact_command_path is not None and (
        carrier_path is None
        or projection_path is None
        or projection_cli_path is None
        or command_path is None
    ):
        raise SmokeError(
            "semantic contact command requires carrier, CK projection, explicit Rust CLI, and semantic pose command"
        )
    if (projection_path is None) != (projection_cli_path is None):
        raise SmokeError("CK projection and its explicit Rust CLI path must be supplied together")
    if carrier_path is None:
        if command_path is not None:
            raise SmokeError("semantic pose command requires --carrier")
        if projection_path is not None:
            raise SmokeError("CK projection requires --carrier")
        selected = neutral_smoke._validate_profile_ids(profile_ids if profile_ids is not None else DEFAULT_PROFILE_IDS)
        _, payload = neutral_smoke.preflight(gallery, selected)
    else:
        carrier_module, carrier, payload, selected, instance_ids = _validated_carrier_input(
            gallery,
            Path(carrier_path),
        )
        if profile_ids is not None and neutral_smoke._validate_profile_ids(profile_ids) != selected:
            raise SmokeError("explicit profile IDs disagree with the validated carrier order")
        carrier_identity = _carrier_identity(carrier, carrier_module)
        carrier_avatar_records = _carrier_avatar_records(carrier)
        if tuple(carrier_identity["experiment_instance_ids"]) != instance_ids:
            raise SmokeError("validated carrier instance order is inconsistent")
        if projection_path is not None:
            _, projection, projection_identity_value = _validated_projection_input(
                gallery,
                Path(carrier_path),
                carrier,
                payload,
                selected,
                instance_ids,
                carrier_identity,
                carrier_avatar_records,
                Path(projection_path),
                Path(projection_cli_path),
            )
        if command_path is not None:
            _, command, command_identity, semantic_payload = _validated_semantic_pose_command(
                gallery,
                Path(carrier_path),
                carrier,
                payload,
                selected,
                instance_ids,
                Path(command_path),
            )
        if package_path is not None:
            _, package_manifest, validated_ck_package = _validated_ck_package_input(
                Path(package_path),
                gallery,
                projection,
                projection_identity_value,
            )
        if contact_command_path is not None:
            _, contact_command, contact_command_identity = _validated_semantic_contact_command(
                gallery,
                Path(carrier_path),
                carrier,
                Path(command_path),
                command,
                command_identity,
                Path(contact_command_path),
            )

    def validate_report(*args: Any, **kwargs: Any) -> None:
        if validated_ck_package is not None:
            kwargs["validated_ck_package"] = validated_ck_package
        _validate_report(*args, **kwargs)

    package_launch_options = (
        {"package_path": Path(package_path), "package_manifest": package_manifest}
        if package_path is not None
        else {}
    )
    if runtime_evaluation:
        if contact_command is None or staged_deformation_captures is None:
            raise SmokeError("runtime evaluation requires validated semantic contact and deformation captures")
        launch_arguments = [
            gallery,
            selected,
            payload,
            carrier_identity,
            carrier_avatar_records,
            command,
            command_identity,
            semantic_payload,
            projection,
            projection_identity_value,
            contact_command,
            contact_command_identity,
            Path(projection_cli_path),
        ]
        launch_identity = _runtime_launch_identity()
        cpu_stdout, cpu_stderr, cpu_returncode, cpu_report = _launch_godot(
            *launch_arguments,
            **package_launch_options,
            deformation_capture=True,
            deformation_capture_sink=staged_deformation_captures.update,
            runtime_measurement_mode="cpu_deformation",
        )
        if cpu_returncode != 0:
            raise SmokeError(
                "Godot cpu_deformation runtime-evaluation launch returned exit code "
                f"{cpu_returncode}; stdout={cpu_stdout!r}; stderr={cpu_stderr!r}"
            )
        if cpu_report is None:
            raise SmokeError("Godot cpu_deformation runtime-evaluation launch returned no report")
        if _runtime_launch_identity() != launch_identity:
            raise SmokeError(
                "runtime evaluation project, script, launcher, or executable identity changed between paired launches"
            )
        rigid_stdout, rigid_stderr, rigid_returncode, rigid_report = _launch_godot(
            *launch_arguments,
            **package_launch_options,
            runtime_measurement_mode="rigid_contact_only",
        )
        if rigid_returncode != 0:
            raise SmokeError(
                "Godot rigid_contact_only runtime-evaluation launch returned exit code "
                f"{rigid_returncode}; stdout={rigid_stdout!r}; stderr={rigid_stderr!r}"
            )
        if rigid_report is None:
            raise SmokeError("Godot rigid_contact_only runtime-evaluation launch returned no report")
        if _runtime_launch_identity() != launch_identity:
            raise SmokeError(
                "runtime evaluation project, script, launcher, or executable identity changed during paired launches"
            )
        validate_report(
            cpu_report,
            payload,
            selected,
            carrier_identity,
            carrier_avatar_records,
            command,
            command_identity,
            projection,
            projection_identity_value,
            contact_command,
            contact_command_identity,
            staged_deformation_captures,
            runtime_measurement_mode="cpu_deformation",
        )
        validate_report(
            rigid_report,
            payload,
            selected,
            carrier_identity,
            carrier_avatar_records,
            command,
            command_identity,
            projection,
            projection_identity_value,
            contact_command,
            contact_command_identity,
            runtime_measurement_mode="rigid_contact_only",
        )
        cpu_report["runtime_measurement"] = _runtime_measurement_with_runner_release(
            cpu_report["runtime_measurement"]
        )
        rigid_report["runtime_measurement"] = _runtime_measurement_with_runner_release(
            rigid_report["runtime_measurement"]
        )
        paired_identities = _runtime_paired_identities(cpu_report, rigid_report, launch_identity)
        runtime_evaluation_value = _build_runtime_evaluation(
            cpu_report,
            rigid_report,
            paired_identities,
            contact_command,
            contact_command_identity,
        )
        cpu_report["runtime_evaluation"] = runtime_evaluation_value
        stdout, stderr, returncode, report = cpu_stdout, cpu_stderr, cpu_returncode, cpu_report
    elif contact_command is not None:
        launch_arguments = [
            gallery,
            selected,
            payload,
            carrier_identity,
            carrier_avatar_records,
            command,
            command_identity,
            semantic_payload,
            projection,
            projection_identity_value,
            contact_command,
            contact_command_identity,
            Path(projection_cli_path),
        ]
        launch_options = {}
        if deformation_captures_path is not None:
            if staged_deformation_captures is None:
                raise SmokeError("semantic deformation captures were not retained in memory")
            launch_options = {
                "deformation_capture": True,
                "deformation_capture_sink": staged_deformation_captures.update,
            }
        stdout, stderr, returncode, report = _launch_godot(
            *launch_arguments,
            **package_launch_options,
            **launch_options,
        )
    elif projection is None and command is None:
        stdout, stderr, returncode, report = _launch_godot(
            gallery,
            selected,
            payload,
            carrier_identity,
            carrier_avatar_records,
            **package_launch_options,
        )
    elif projection is None:
        stdout, stderr, returncode, report = _launch_godot(
            gallery,
            selected,
            payload,
            carrier_identity,
            carrier_avatar_records,
            command,
            command_identity,
            semantic_payload,
            **package_launch_options,
        )
    elif command is None:
        stdout, stderr, returncode, report = _launch_godot(
            gallery,
            selected,
            payload,
            carrier_identity,
            carrier_avatar_records,
            projection=projection,
            projection_identity=projection_identity_value,
            **package_launch_options,
        )
    else:
        stdout, stderr, returncode, report = _launch_godot(
            gallery,
            selected,
            payload,
            carrier_identity,
            carrier_avatar_records,
            command,
            command_identity,
            semantic_payload,
            projection,
            projection_identity_value,
            projection_cli_path=Path(projection_cli_path),
            **package_launch_options,
        )
    if returncode != 0:
        raise SmokeError(f"Godot launcher returned exit code {returncode}; stdout={stdout!r}; stderr={stderr!r}")
    if report is None:
        raise SmokeError("Godot returned success without a skeletal-pose report")
    if runtime_evaluation:
        # Both reports were validated above, and the paired object was built
        # from their independently checked raw measurements.
        pass
    elif contact_command is not None:
        validation_arguments = [
            report,
            payload,
            selected,
            carrier_identity,
            carrier_avatar_records,
            command,
            command_identity,
            projection,
            projection_identity_value,
            contact_command,
            contact_command_identity,
        ]
        if deformation_captures_path is not None:
            if staged_deformation_captures is None:
                raise SmokeError("semantic deformation captures were not retained in memory")
            validation_arguments.append(staged_deformation_captures)
        validate_report(*validation_arguments)
    elif projection is None and command is None:
        validate_report(report, payload, selected, carrier_identity, carrier_avatar_records)
    elif projection is None:
        validate_report(
            report,
            payload,
            selected,
            carrier_identity,
            carrier_avatar_records,
            command,
            command_identity,
        )
    elif command is None:
        validate_report(
            report,
            payload,
            selected,
            carrier_identity,
            carrier_avatar_records,
            projection=projection,
            projection_identity=projection_identity_value,
        )
    else:
        validate_report(
            report,
            payload,
            selected,
            carrier_identity,
            carrier_avatar_records,
            command,
            command_identity,
            projection,
            projection_identity_value,
        )
    if carrier_path is None:
        _, post_payload = neutral_smoke.preflight(gallery, selected)
        if post_payload != payload:
            raise SmokeError("validated gallery projection changed during the skeletal-pose smoke; refusing to publish a success report")
    else:
        post_module, post_carrier, post_payload, post_profiles, post_instances = _validated_carrier_input(
            gallery,
            Path(carrier_path),
        )
        post_carrier_identity = _carrier_identity(post_carrier, post_module)
        if (
            post_payload != payload
            or post_profiles != selected
            or post_instances != instance_ids
            or post_carrier_identity != carrier_identity
        ):
            raise SmokeError("validated carrier or gallery changed during the skeletal-pose smoke; refusing to publish a success report")
        if command_path is not None:
            _, post_command, post_command_identity, post_semantic_payload = _validated_semantic_pose_command(
                gallery,
                Path(carrier_path),
                post_carrier,
                post_payload,
                post_profiles,
                post_instances,
                Path(command_path),
            )
            if (
                post_command != command
                or post_command_identity != command_identity
                or post_semantic_payload != semantic_payload
            ):
                raise SmokeError("semantic pose command, carrier, or gallery changed during the skeletal-pose smoke; refusing to publish a success report")
        if contact_command_path is not None:
            _, post_contact_command, post_contact_identity = _validated_semantic_contact_command(
                gallery,
                Path(carrier_path),
                post_carrier,
                Path(command_path),
                post_command,
                post_command_identity,
                Path(contact_command_path),
            )
            if post_contact_command != contact_command or post_contact_identity != contact_command_identity:
                raise SmokeError(
                    "semantic contact command, pose command, carrier, or gallery changed during the skeletal-pose smoke; refusing to publish a success report"
                )
        if projection_path is not None:
            _, post_projection, post_projection_identity = _validated_projection_input(
                gallery,
                Path(carrier_path),
                post_carrier,
                post_payload,
                post_profiles,
                post_instances,
                post_carrier_identity,
                _carrier_avatar_records(post_carrier),
                Path(projection_path),
                Path(projection_cli_path),
            )
            if post_projection != projection or post_projection_identity != projection_identity_value:
                raise SmokeError("CK projection changed during the skeletal-pose smoke; refusing to publish a success report")
            if package_path is not None:
                _, post_package_manifest, post_validated_ck_package = _validated_ck_package_input(
                    Path(package_path),
                    gallery,
                    post_projection,
                    post_projection_identity,
                )
                if (
                    post_package_manifest != package_manifest
                    or post_validated_ck_package != validated_ck_package
                ):
                    raise SmokeError(
                        "CK package changed during the skeletal-pose smoke; refusing to publish a success report"
                    )
    _publish_deformation_result(
        report_path,
        report,
        deformation_captures_path,
        staged_deformation_captures,
    )
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gallery", required=True, type=Path, help="absolute completed structural gallery directory")
    parser.add_argument("--carrier", type=Path, help="optional absolute disposable avatar-input carrier path")
    parser.add_argument("--command", "--semantic-pose-command", dest="command_path", type=Path, help="optional absolute semantic-pose command; requires --carrier")
    parser.add_argument(
        "--contact-command",
        "--semantic-contact-command",
        dest="contact_command_path",
        type=Path,
        help="optional experiment-local semantic-contact command; requires carrier, projection, CK CLI, and semantic pose command",
    )
    parser.add_argument("--projection", dest="projection_path", type=Path, help="optional absolute disposable CK projection; requires --carrier")
    parser.add_argument("--ck-cli", dest="projection_cli_path", type=Path, help="explicit absolute native creature-kernel CLI path; requires --projection")
    parser.add_argument("--profile-id", action="append", dest="profile_ids", help="repeat exactly twice; defaults to the compact and tall frozen IDs")
    parser.add_argument("--report", required=True, type=Path, help="absolute report path")
    parser.add_argument(
        "--deformation-captures",
        dest="deformation_captures_path",
        type=Path,
        help="optional absolute, not-yet-existing output directory for the three deformation captures; requires full semantic contact mode",
    )
    parser.add_argument(
        "--runtime-evaluation",
        action="store_true",
        help=(
            "run matched cpu_deformation and rigid_contact_only measurements and publish one paired report "
            "only after both succeed; requires the full deformation-capture/contact predecessor set"
        ),
    )
    parser.add_argument(
        "--package",
        dest="package_path",
        type=Path,
        help=(
            "optional absolute disposable CK package directory; requires carrier, CK projection, "
            "explicit CK CLI, and semantic-pose command"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        profile_ids = tuple(args.profile_ids) if args.profile_ids is not None else (None if args.carrier is not None else DEFAULT_PROFILE_IDS)
        report = run_skeletal_pose_smoke(
            args.gallery,
            profile_ids,
            args.report,
            args.carrier,
            args.command_path,
            args.projection_path,
            args.projection_cli_path,
            args.contact_command_path,
            args.deformation_captures_path,
            args.runtime_evaluation,
            args.package_path,
        )
    except SmokeError as exc:
        print(f"skeletal pose smoke failed: {exc}", file=sys.stderr)
        return 2
    print(neutral_smoke._canonical_json(report).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

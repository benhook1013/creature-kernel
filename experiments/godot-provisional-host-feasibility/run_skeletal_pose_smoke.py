#!/usr/bin/env python3
"""Run a disposable Godot Skeleton3D/Skin shared-pose binding smoke."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any


sys.dont_write_bytecode = True

EXPERIMENT_ROOT = Path(__file__).resolve().parent
NEUTRAL_RUNNER_PATH = EXPERIMENT_ROOT / "run_structural_gallery_smoke.py"
CARRIER_MODULE_PATH = EXPERIMENT_ROOT / "disposable_avatar_carrier.py"
COMMAND_MODULE_PATH = EXPERIMENT_ROOT / "disposable_semantic_pose_command.py"
CONTACT_COMMAND_MODULE_PATH = EXPERIMENT_ROOT / "disposable_semantic_contact_command.py"
PROJECTION_MODULE_PATH = EXPERIMENT_ROOT / "disposable_ck_projection.py"
GODOT_SCRIPT = EXPERIMENT_ROOT / "skeletal_pose_smoke.gd"
VISIBLE_GODOT_OPT_IN = "CK_ALLOW_VISIBLE_GODOT"
_CARRIER_MODULE: Any | None = None
_COMMAND_MODULE: Any | None = None
_CONTACT_COMMAND_MODULE: Any | None = None
_PROJECTION_MODULE: Any | None = None


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
    if not isinstance(snapshots, dict) or set(snapshots) != {"initial", "contact", "final"}:
        raise SmokeError("semantic contact response snapshots are incomplete or aliased")
    initial = _validate_contact_snapshot(snapshots["initial"], "initial", "semantic contact response initial")
    contact = _validate_contact_snapshot(snapshots["contact"], "contact", "semantic contact response contact")
    final = _validate_contact_snapshot(snapshots["final"], "final", "semantic contact response final")

    initial_trace = trace_by_tick.get(initial["tick"])
    if initial["tick"] != 0 or initial_trace is None or initial_trace["phase"] != "setup" or initial_trace["contact_count"] != 0:
        raise SmokeError("semantic contact initial snapshot does not match setup tick evidence")
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
    for label, snapshot in (("initial", initial), ("contact", contact), ("final", final)):
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
) -> None:
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
    expected_report_boundary = CONTACT_REPORT_BOUNDARY if semantic_contact_command is not None else REPORT_BOUNDARY
    if report.get("boundary") != expected_report_boundary:
        raise SmokeError("Godot skeletal-pose report boundary is invalid")
    expected_claims = CONTACT_REPORT_CLAIMS if semantic_contact_command is not None else REPORT_CLAIMS
    if report.get("claims") != expected_claims:
        raise SmokeError("Godot skeletal-pose report contains an unexpected claim")
    expected_scope_flags = CONTACT_REPORT_FLAGS if semantic_contact_command is not None else REPORT_FLAGS
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
    contact_report_keys = {"semantic_contact", *CONTACT_REPORT_ALIAS_KEYS}
    if semantic_contact_command is None:
        if contact_report_keys.intersection(report):
            raise SmokeError("no-contact Godot report contains unexpected semantic contact evidence")
    else:
        if contact_command_identity is None:
            raise SmokeError("semantic contact command identity expectation is missing")
        _validate_contact_report(report, semantic_contact_command, contact_command_identity)
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
) -> tuple[str, str, int, dict[str, Any] | None]:
    """Launch with a real renderer; headless mode exposes dummy rendering RIDs."""
    if os.environ.get(VISIBLE_GODOT_OPT_IN) != "1":
        raise SmokeError(
            f"visible X11 Godot launch is disabled; set {VISIBLE_GODOT_OPT_IN}=1 "
            "only for an attended run"
        )
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
        shutil.copyfile(neutral_smoke.PROJECT_FILE, project)
        shutil.copyfile(GODOT_SCRIPT, script_path)
        launch_command = [
            str(neutral_smoke.LAUNCHER),
            "--display-driver",
            "x11",
            "--rendering-method",
            "gl_compatibility",
            "--audio-driver",
            "Dummy",
            "--path",
            str(Path(temporary)),
            "--script",
            str(script_path),
            "--",
            "--gallery",
            str(gallery),
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
) -> dict[str, Any]:
    report_path = neutral_smoke._validate_report_destination(report_path)
    gallery = Path(gallery)
    carrier_identity = None
    carrier_avatar_records = None
    command = None
    command_identity = None
    semantic_payload = None
    projection = None
    projection_identity_value = None
    contact_command = None
    contact_command_identity = None
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
    if contact_command is not None:
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
            contact_command,
            contact_command_identity,
            Path(projection_cli_path),
        )
    elif projection is None and command is None:
        stdout, stderr, returncode, report = _launch_godot(
            gallery,
            selected,
            payload,
            carrier_identity,
            carrier_avatar_records,
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
        )
    if returncode != 0:
        raise SmokeError(f"Godot launcher returned exit code {returncode}; stdout={stdout!r}; stderr={stderr!r}")
    if report is None:
        raise SmokeError("Godot returned success without a skeletal-pose report")
    if contact_command is not None:
        _validate_report(
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
        )
    elif projection is None and command is None:
        _validate_report(report, payload, selected, carrier_identity, carrier_avatar_records)
    elif projection is None:
        _validate_report(
            report,
            payload,
            selected,
            carrier_identity,
            carrier_avatar_records,
            command,
            command_identity,
        )
    elif command is None:
        _validate_report(
            report,
            payload,
            selected,
            carrier_identity,
            carrier_avatar_records,
            projection=projection,
            projection_identity=projection_identity_value,
        )
    else:
        _validate_report(
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
    neutral_smoke._publish_report(report_path, report)
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
        )
    except SmokeError as exc:
        print(f"skeletal pose smoke failed: {exc}", file=sys.stderr)
        return 2
    print(neutral_smoke._canonical_json(report).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

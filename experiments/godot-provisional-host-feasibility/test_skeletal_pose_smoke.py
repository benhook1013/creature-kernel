from __future__ import annotations

from copy import deepcopy
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
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw, ImageOps


HERE = Path(__file__).resolve()
EXPERIMENT = HERE.parent
REPOSITORY_ROOT = HERE.parents[2]
GALLERY = Path(os.environ.get("CK_GODOT_STRUCTURAL_GALLERY", "/tmp/ck-godot-structural-inputs/gallery"))
REAL_CLI = HERE.parents[2] / "target" / "debug" / "creature-kernel"
DEFAULTS = ("compact_broad_short_limb_large_head", "tall_narrow_long_legged")
ALTERNATE = ("slender_long_limb", "stocky_broad_chested")
FAIL_CLOSED_PROJECTION_DIAGNOSTIC = (
    "skeletal pose smoke failed: selected profile IDs disagree with the validated projection"
)
CARRIER_IDENTITY = {
    "sha256": "e" * 64,
    "byte_count_decimal": "1234",
    "schema": "creature-kernel.disposable-engine-neutral-avatar-input.v1",
    "boundary": "experiment_input_only_no_runtime_package_or_adapter_contract",
    "experiment_instance_ids": ["avatar-left", "avatar-right"],
}
CARRIER_AVATAR_RECORDS = [
    {
        "instance_id": "avatar-left",
        "profile_id": DEFAULTS[0],
        "candidate_profile_sha256": "a" * 64,
    },
    {
        "instance_id": "avatar-right",
        "profile_id": DEFAULTS[1],
        "candidate_profile_sha256": "b" * 64,
    },
]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


smoke = load_module("skeletal_pose_smoke_under_test", EXPERIMENT / "run_skeletal_pose_smoke.py")
sys.modules["run_structural_gallery_smoke"] = smoke.neutral_smoke
carrier = load_module("disposable_avatar_carrier_for_skeletal_tests", EXPERIMENT / "disposable_avatar_carrier.py")
sys.modules["disposable_avatar_carrier"] = carrier
projection = load_module("disposable_ck_projection_for_skeletal_tests", EXPERIMENT / "disposable_ck_projection.py")
semantic_command = load_module(
    "disposable_semantic_pose_command_for_skeletal_tests",
    EXPERIMENT / "disposable_semantic_pose_command.py",
)


def _contact_command_fixture() -> tuple[dict, dict]:
    command = {
        "schema": smoke.CONTACT_COMMAND_SCHEMA,
        "boundary": smoke.CONTACT_COMMAND_BOUNDARY,
        "command_id": smoke.CONTACT_COMMAND_ID,
        "command_version": smoke.CONTACT_COMMAND_VERSION,
        "mapping_revision": smoke.CONTACT_MAPPING_REVISION,
        "targets": deepcopy(CARRIER_AVATAR_RECORDS),
        "source_pose_command": {
            "sha256": "p" * 64,
            "byte_count_decimal": "1",
            "schema": semantic_command.SCHEMA,
            "boundary": semantic_command.BOUNDARY,
            "command_id": semantic_command.COMMAND_ID,
            "command_version": semantic_command.COMMAND_VERSION,
        },
        "participants": deepcopy(smoke.CONTACT_PARTICIPANTS),
        "interaction": deepcopy(smoke.CONTACT_INTERACTION),
    }
    identity = {
        "sha256": "c" * 64,
        "byte_count_decimal": "1",
        "schema": command["schema"],
        "boundary": command["boundary"],
        "command_id": command["command_id"],
        "command_version": command["command_version"],
    }
    return command, identity


def _contact_report_fixture(command: dict, identity: dict) -> dict:
    def transform(x: float) -> list[float]:
        return [
            1.0,
            0.0,
            0.0,
            x,
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

    participants = []
    selector_mappings = []
    for index, participant in enumerate(smoke.CONTACT_PARTICIPANTS):
        posed_proxy = {
            "a": [0.0, 0.0, 0.0],
            "b": [0.0, 1.0, 0.0],
            "bone_id": smoke.CONTACT_BONE_IDS[index],
            "kind": "capsule",
            "owned_part": deepcopy(smoke.CONTACT_OWNED_PARTS[index]),
            "partition_rule": smoke.CONTACT_PROXY_PARTITION_RULE,
            "partition_vertex_count": 100 + index,
            "radius": 0.25,
            "radius_rule": smoke.CONTACT_PROXY_RADIUS_RULE,
        }
        participants.append(
            {
                **deepcopy(participant),
                "target": deepcopy(command["targets"][index]),
                "source_joint": deepcopy(smoke.CONTACT_SOURCE_JOINTS[index]),
                "source_bone_id": smoke.CONTACT_BONE_IDS[index],
                "source_proxy_index": smoke.CONTACT_SHAPE_INDICES[index],
                "posed_proxy": posed_proxy,
                "runtime_shape_index": smoke.CONTACT_RUNTIME_SHAPE_INDICES[index],
            }
        )
        selector_mappings.append(
            {
                **deepcopy(participant),
                "bone_id": smoke.CONTACT_BONE_IDS[index],
                "proxy_id": smoke.CONTACT_BONE_IDS[index],
                "owned_part": deepcopy(smoke.CONTACT_OWNED_PARTS[index]),
                "shape_index": smoke.CONTACT_SHAPE_INDICES[index],
                "runtime_shape_index": smoke.CONTACT_RUNTIME_SHAPE_INDICES[index],
            }
        )
    phase_ticks = []
    contact_tick_evidence = [{"tick": 0, "phase": "setup", "contact_count": 0}]
    start_tick = 1
    for phase, ticks in zip(smoke.CONTACT_PHASE_ORDER, smoke.CONTACT_PHASE_TICKS):
        end_tick = start_tick + ticks - 1
        phase_ticks.append(
            {"phase": phase, "ticks": ticks, "start_tick": start_tick, "end_tick": end_tick}
        )
        for tick in range(start_tick, end_tick + 1):
            contact_tick_evidence.append(
                {"tick": tick, "phase": phase, "contact_count": 1 if phase == "contact" else 0}
            )
        start_tick = end_tick + 1
    def snapshot(label: str, tick: int, position_x: float, linear_velocity: list[float]) -> dict:
        return {
            "label": label,
            "tick": tick,
            "transform": transform(position_x),
            "position": [position_x, 0.0, 0.0],
            "linear_velocity": linear_velocity,
            "angular_velocity": [0.0, 0.0, 0.0],
        }

    return {
        "command_identity": deepcopy(identity),
        "targets": deepcopy(command["targets"]),
        "source_pose_command": deepcopy(command["source_pose_command"]),
        "mapping_revision": smoke.CONTACT_MAPPING_REVISION,
        "participants": participants,
        "interaction": deepcopy(smoke.CONTACT_INTERACTION),
        "selector_mappings": selector_mappings,
        "physics_configuration": {
            "physics_engine": "Jolt Physics",
            "actuator_body": "AnimatableBody3D",
            "actuator_sync_to_physics": True,
            "response_body": "RigidBody3D",
            "response_mass": 1.0,
            "response_gravity_scale": 0.0,
            "response_can_sleep": False,
            "response_rotation_locked": True,
            "response_contact_monitor": True,
            "response_max_contacts_reported": 8,
            "one_shape_per_contact_body": True,
        },
        "phase_order": deepcopy(smoke.CONTACT_PHASE_ORDER),
        "max_ticks": smoke.CONTACT_MAX_TICKS,
        "phase_ticks": phase_ticks,
        "contact_tick_evidence": contact_tick_evidence,
        "solver_impulses": [
            {
                "runtime_derived": True,
                "target_indices": [0, 1],
                "shape_indices": list(smoke.CONTACT_SHAPE_INDICES),
                "impulse_magnitude": 0.25,
                "contact_samples": [
                    {
                        "contact_index": 0,
                        "collider_id": 42,
                        "collider_object_id": 42,
                        "collider_shape_index": 0,
                        "local_shape_index": 0,
                        "point": [0.25, 0.0, 0.0],
                        "normal": [1.0, 0.0, 0.0],
                        "impulse": [0.25, 0.0, 0.0],
                        "tick": 25,
                        "phase": "contact",
                    }
                ],
            }
        ],
        "response": {
            "target_index": 1,
            "shape_index": smoke.CONTACT_SHAPE_INDICES[1],
            "normal": [1.0, 0.0, 0.0],
            "snapshots": {
                "initial": snapshot("initial", 0, 0.0, [0.0, 0.0, 0.0]),
                "contact": snapshot("contact", 25, 0.05, [0.1, 0.0, 0.0]),
                "final": snapshot("final", smoke.CONTACT_TOTAL_TICKS, 0.1, [0.05, 0.0, 0.0]),
            },
            "normal_velocity_delta": 0.1,
            "normal_displacement": 0.1,
            "displacement": 0.1,
        },
    }


def _encode_png(image: Image.Image) -> bytes:
    output = BytesIO()
    image.save(output, format="PNG", optimize=False)
    return output.getvalue()


def _png_fixture(*, peak: bool = False, blank: bool = False) -> bytes:
    size = (smoke.DEFORMATION_CAPTURE_WIDTH, smoke.DEFORMATION_CAPTURE_HEIGHT)
    background = (9, 11, 16, 255)
    image = Image.new("RGBA", size, background)
    if not blank:
        draw = ImageDraw.Draw(image)
        for view_index in range(3):
            left = view_index * smoke.DEFORMATION_CAPTURE_WIDTH // 3
            right = (view_index + 1) * smoke.DEFORMATION_CAPTURE_WIDTH // 3
            draw.rectangle((left + 80, 64, right - 80, 448), fill=(52, 64, 84, 255))
            for stripe in range(32):
                colour = (52 + stripe, 64 + (stripe * 3) % 48, 84 + (stripe * 5) % 64, 255)
                y = 72 + stripe * 11
                draw.line((left + 88, y, right - 88, y), fill=colour, width=8)
            draw.ellipse(
                (left + 150, 130, right - 150, 382),
                fill=(117, 135, 158, 255),
                outline=(232, 170, 105, 255),
                width=5,
            )
            draw.line((left + 120, 256, right - 120, 256), fill=(245, 225, 170, 255), width=7)
            if peak:
                draw.ellipse((left + 222, 202, left + 330, 310), fill=(199, 76, 44, 255))
                draw.rectangle((left + 244, 212, left + 282, 300), fill=(236, 119, 60, 255))
    return _encode_png(image)


def _one_pixel_delta(data: bytes) -> bytes:
    with Image.open(BytesIO(data)) as source:
        image = source.convert("RGBA")
    pixel = image.getpixel((0, 0))
    image.putpixel((0, 0), (255 - pixel[0], pixel[1], pixel[2], pixel[3]))
    return _encode_png(image)


def _capture_evidence_for_bytes(report: dict, captures: dict[str, bytes]) -> dict:
    evidence = deepcopy(report["semantic_deformation"])
    for record, file_name in zip(evidence["captures"], smoke.DEFORMATION_CAPTURE_NAMES):
        data = captures[file_name]
        record["sha256"] = hashlib.sha256(data).hexdigest()
        record["byte_count_decimal"] = str(len(data))
    return evidence


def _deformation_report_fixture() -> tuple[dict, dict, dict, dict, dict[str, bytes]]:
    payload, report = _skeletal_validation_fixture()
    command, identity = _contact_command_fixture()
    contact_evidence = _contact_report_fixture(command, identity)
    reference = smoke._reconstruct_deformation_baseline_vertices(
        0.25,
        1.0,
        smoke._deformation_capsule_basis([0.0, 0.0, 0.0], [0.0, 1.0, 0.0]),
    )
    deformation_center = [0.25, 0.0, 0.0]
    falloff_radius = 0.25 * smoke.DEFORMATION_FALLOFF_RADIUS_RATIO
    raw_weights = []
    for vertex in reference:
        distance = math.sqrt(
            sum((coordinate - center_coordinate) ** 2 for coordinate, center_coordinate in zip(vertex, deformation_center))
        )
        raw_weights.append(max(0.0, 1.0 - distance / falloff_radius) ** 2 if distance < falloff_radius else 0.0)
    raw_weight_max = max(raw_weights)
    weights = [weight / raw_weight_max for weight in raw_weights]
    absolute_depth = 0.25 * smoke.DEFORMATION_NORMALIZED_PEAK_DEPTH
    inward = [-1.0, 0.0, 0.0]
    peak = [
        [coordinate + inward[axis] * absolute_depth * weight for axis, coordinate in enumerate(vertex)]
        for vertex, weight in zip(reference, weights)
    ]
    residuals = [absolute_depth * weight for weight in weights]
    peak_max = max(residuals)
    affected = sum(weight > 0.0 for weight in weights)
    states = {
        "reference": {
            "tick": 0,
            "normalized_depth": 0.0,
            "vertices": deepcopy(reference),
            "max_residual": 0.0,
            "affected_vertex_count": 0,
            "outside_falloff_max_residual": 0.0,
        },
        "peak": {
            "tick": 25,
            "normalized_depth": smoke.DEFORMATION_NORMALIZED_PEAK_DEPTH,
            "vertices": peak,
            "max_residual": peak_max,
            "affected_vertex_count": affected,
            "outside_falloff_max_residual": 0.0,
        },
        "recovered": {
            "tick": smoke.DEFORMATION_RECOVERY_TICK,
            "normalized_depth": 0.0,
            "vertices": deepcopy(reference),
            "max_residual": 0.0,
            "affected_vertex_count": 0,
            "outside_falloff_max_residual": 0.0,
        },
    }
    reference_capture = _png_fixture()
    captures = {
        "reference.png": reference_capture,
        "peak.png": _png_fixture(peak=True),
        "recovered.png": reference_capture,
    }
    report.update(
        {
            "boundary": smoke.DEFORMATION_REPORT_BOUNDARY,
            "claims": deepcopy(smoke.DEFORMATION_REPORT_CLAIMS),
            "scope_flags": deepcopy(smoke.DEFORMATION_REPORT_FLAGS),
            "coordinate_rule": {
                "kind": "disposable_host_local_identity",
                "mapping": "CK XYZ -> Godot XYZ: x->x, y->y, z->z",
                "scope": smoke.DEFORMATION_REPORT_BOUNDARY,
                "profile_translations": [list(value) for value in smoke.EXPECTED_TRANSLATIONS],
            },
            "pose_binding": {
                "pose_id": "test-pose",
                "pose_sha256": "d" * 64,
                "path": "structural_embodiment_shared_pose.json",
                "rule_count": 18,
                "rules_validated": True,
                "applied_to_skeleton3d": True,
                "ik": False,
                "contact": True,
            },
            "semantic_contact": contact_evidence,
            "semantic_deformation": {
                "boundary": smoke.DEFORMATION_REPORT_BOUNDARY,
                "target_index": 1,
                "source_bone_id": smoke.CONTACT_BONE_IDS[1],
                "source_shape_index": smoke.CONTACT_SHAPE_INDICES[1],
                "runtime_shape_index": smoke.CONTACT_RUNTIME_SHAPE_INDICES[1],
                "surface": {
                    "kind": smoke.DEFORMATION_SURFACE_KIND,
                    "attachment": smoke.DEFORMATION_SURFACE_ATTACHMENT,
                    "collision_mode": smoke.DEFORMATION_SURFACE_COLLISION_MODE,
                    "axial_segments": smoke.DEFORMATION_AXIAL_SEGMENTS,
                    "radial_segments": smoke.DEFORMATION_RADIAL_SEGMENTS,
                    "vertex_count": smoke.DEFORMATION_VERTEX_COUNT,
                    "triangle_count": smoke.DEFORMATION_TRIANGLE_COUNT,
                    "baseline_radius": 0.25,
                    "baseline_length": 1.0,
                },
                "drive": {
                    "kind": smoke.DEFORMATION_DRIVE_KIND,
                    "normalized_peak_depth": smoke.DEFORMATION_NORMALIZED_PEAK_DEPTH,
                    "absolute_peak_depth": absolute_depth,
                    "falloff_radius_ratio": smoke.DEFORMATION_FALLOFF_RADIUS_RATIO,
                    "peak_tick": 25,
                    "contact_sample_tick": 25,
                    "contact_sample_index": 0,
                    "sample_response_transform": [
                        1.0, 0.0, 0.0, 0.05,
                        0.0, 1.0, 0.0, 0.0,
                        0.0, 0.0, 1.0, 0.0,
                        0.0, 0.0, 0.0, 1.0,
                    ],
                    "runtime_contact_point": [0.25, 0.0, 0.0],
                    "local_contact_point": [0.20, 0.0, 0.0],
                    "local_deformation_center": deformation_center,
                    "local_inward_direction": inward,
                    "falloff_weights": weights,
                },
                "states": states,
                "captures": [
                    {
                        "label": label,
                        "file_name": file_name,
                        "width": smoke.DEFORMATION_CAPTURE_WIDTH,
                        "height": smoke.DEFORMATION_CAPTURE_HEIGHT,
                        "sha256": hashlib.sha256(captures[file_name]).hexdigest(),
                        "byte_count_decimal": str(len(captures[file_name])),
                    }
                    for label, file_name in zip(smoke.DEFORMATION_CAPTURE_LABELS, smoke.DEFORMATION_CAPTURE_NAMES)
                ],
            },
        }
    )
    return payload, report, command, identity, captures


def _scale_reported_deformation_falloff(report: dict, factor: float) -> None:
    evidence = report["semantic_deformation"]
    drive = evidence["drive"]
    reference = evidence["states"]["reference"]["vertices"]
    peak_state = evidence["states"]["peak"]
    absolute_depth = drive["absolute_peak_depth"]
    inward = drive["local_inward_direction"]
    scaled_weights = [float(weight) * factor for weight in drive["falloff_weights"]]
    drive["falloff_weights"] = scaled_weights
    peak_state["vertices"] = [
        [coordinate + inward[axis] * absolute_depth * weight for axis, coordinate in enumerate(vertex)]
        for vertex, weight in zip(reference, scaled_weights)
    ]
    peak_state["max_residual"] = absolute_depth * max(scaled_weights)


def _remove_first_positive_falloff_weight(report: dict) -> None:
    weights = report["semantic_deformation"]["drive"]["falloff_weights"]
    index = next(index for index, weight in enumerate(weights) if float(weight) > 0.0)
    weights[index] = 0.0


def _projection_fixture(payload: dict, carrier_value: dict | None = None) -> tuple[dict, dict, dict, list[dict], tuple[str, str]]:
    projected_payload = deepcopy(payload)
    for profile in projected_payload["profiles"]:
        profile_id = profile["profile_id"]
        profile["artifacts"] = [
            {
                "path": f"{profile_id}/{name}",
                "sha256": hashlib.sha256(f"{profile_id}/{name}".encode()).hexdigest(),
                "bytes": index + 1,
            }
            for index, name in enumerate(smoke.EXPECTED_ARTIFACT_NAMES)
        ]
    records = deepcopy(CARRIER_AVATAR_RECORDS)
    carrier_instances = [
        {
            **record,
            "label": f"Fixture {record['profile_id']}",
            "artifacts": deepcopy(profile["artifacts"]),
            "metrics": deepcopy(profile["metrics"]),
        }
        for record, profile in zip(records, projected_payload["profiles"])
    ]
    carrier_value = carrier_value or {
        "schema": carrier.SCHEMA,
        "boundary": carrier.BOUNDARY,
        "source_gallery": {
            "projection_contract": projected_payload["projection_contract"],
            "manifest_sha256": projected_payload["manifest_sha256"],
            "manifest_bytes": projected_payload["manifest_bytes"],
            "boundary": projected_payload["boundary"],
        },
        "shared_pose": {
            "path": carrier.POSE_FILE,
            "pose_id": projected_payload["pose_id"],
            "sha256": projected_payload["pose_sha256"],
            "bytes": 1,
        },
        "instances": carrier_instances,
    }
    carrier_value["schema"] = carrier.SCHEMA
    carrier_module = SimpleNamespace(
        SCHEMA=carrier.SCHEMA,
        BOUNDARY=carrier.BOUNDARY,
        _canonical_json=lambda value: (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode(),
    )
    carrier_identity = smoke._carrier_identity(carrier_value, carrier_module)
    projection_body = {
        "schema": projection.SCHEMA,
        "boundary": projection.BOUNDARY,
        "producer_identity": {
            "sha256": "9" * 64,
            "bytes": 1,
            "operation": projection.RUST_OPERATION,
            "format": projection.RUST_FORMAT,
        },
        "carrier_identity": {
            "schema": carrier.SCHEMA,
            "boundary": carrier.BOUNDARY,
            "sha256": carrier_identity["sha256"],
            "bytes": int(carrier_identity["byte_count_decimal"]),
            "instance_ids": [record["instance_id"] for record in records],
        },
        "gallery_identity": {
            "projection_contract": projected_payload["projection_contract"],
            "manifest_sha256": projected_payload["manifest_sha256"],
            "manifest_bytes": projected_payload["manifest_bytes"],
            "boundary": projected_payload["boundary"],
            "profile_ids": list(DEFAULTS),
        },
        "shared_pose": deepcopy(carrier_value["shared_pose"]),
        "avatars": [
            {
                "instance_id": record["instance_id"],
                "profile_id": record["profile_id"],
                "label": f"Fixture {record['profile_id']}",
                "candidate_profile_sha256": profile["candidate_profile_sha256"],
                "source": {
                    "path": f"sources/{record['profile_id']}.json",
                    "sha256": "f" * 64,
                    "bytes": 1,
                    "document": f"fixture.{record['profile_id']}",
                    "namespace": "fixture",
                },
                "rust_inspection": {},
                "artifacts": deepcopy(profile["artifacts"]),
                "metrics": deepcopy(profile["metrics"]),
            }
            for record, profile in zip(records, projected_payload["profiles"])
        ],
    }
    projection_body_bytes = (json.dumps(projection_body, sort_keys=True, separators=(",", ":")) + "\n").encode()
    identity = {
        "scope": projection.PROJECTION_IDENTITY_SCOPE,
        "sha256": hashlib.sha256(projection_body_bytes).hexdigest(),
        "bytes": len(projection_body_bytes),
    }
    projection_value = {
        "schema": projection_body["schema"],
        "boundary": projection_body["boundary"],
        "projection_identity": identity,
        "producer_identity": projection_body["producer_identity"],
        "carrier_identity": projection_body["carrier_identity"],
        "gallery_identity": projection_body["gallery_identity"],
        "shared_pose": projection_body["shared_pose"],
        "avatars": projection_body["avatars"],
    }
    return projection_value, identity, carrier_value, records, DEFAULTS


def _skeletal_validation_fixture() -> tuple[dict, dict]:
    payload_profiles = []
    actual_profiles = []
    candidate_hashes = {}
    artifact_identities = {}
    for index, profile_id in enumerate(DEFAULTS):
        candidate_hash = chr(ord("a") + index) * 64
        metrics = {
            "format": "creature-kernel.disposable-structural-embodiment-gallery.v1",
            "profile_id": profile_id,
            "neutral_vertex_count": 3,
            "posed_vertex_count": 3,
            "face_count": 1,
            "bone_count": 18,
            "proxy_count": 18,
            "neutral_bounds": {"min": [0.0, 0.0, 0.0], "max": [1.0, 1.0, 1.0]},
            "posed_bounds": {"min": [0.0, 0.0, 0.0], "max": [1.0, 1.0, 1.0]},
            "pose_rule_count": 18,
            "source_joint_frame_policy": "identity-only-validated-from-hash-bound-structure",
            "gallery_global_world_bound": {"min": [-1.0, -1.0, -1.0], "max": [1.0, 1.0, 1.0]},
        }
        payload_profiles.append(
            {
                "profile_id": profile_id,
                "candidate_profile_sha256": candidate_hash,
                "artifacts": [],
                "metrics": metrics,
            }
        )
        candidate_hashes[profile_id] = candidate_hash
        artifact_identities[profile_id] = []
        actual_profiles.append(
            {
                "profile_id": profile_id,
                "candidate_profile_sha256": candidate_hash,
                "metrics": deepcopy(metrics),
                "counts": {
                    "neutral_vertex_count": 3,
                    "posed_vertex_count": 3,
                    "face_count": 1,
                    "bone_count": 18,
                    "proxy_count": 18,
                    "weight_vertex_count": 3,
                    "influence_count": 18,
                },
                "neutral_mesh_aabb": metrics["neutral_bounds"],
                "posed_mesh_aabb": metrics["posed_bounds"],
                "posed_proxy_aabb": {"min": [0.0, 0.0, 0.0], "max": [1.0, 1.0, 1.0]},
                "profile_translation": list(smoke.EXPECTED_TRANSLATIONS[index]),
                "node_counts": {
                    "profile_root": 1,
                    "skeleton_3d": 1,
                    "mesh_instance_3d": 1,
                    "static_body_3d": 1,
                    "collision_shape_3d": 18,
                    "total_profile_nodes": 22,
                },
                "binding": {
                    "skeleton_bone_count": 18,
                    "skin_bind_count": 18,
                    "unique_bone_names": True,
                    "parent_links_match": True,
                    "neutral_rest_matches_published": True,
                    "skin_bind_poses_match_published": True,
                    "mesh_skeleton_path_bound": True,
                    "mesh_skin_bound": True,
                    "neutral_baked_mesh_matches": True,
                    "posed_baked_mesh_matches": True,
                    "pose_rules_applied": 18,
                    "pose_global_matrices_match": 18,
                    "skin_matrices_match": 18,
                    "posed_proxy_nodes_match": 18,
                    "tolerance": smoke.TOLERANCE,
                    "normal_tolerance": smoke.NORMAL_TOLERANCE,
                    "max_neutral_vertex_error": 0.0,
                    "max_neutral_normal_error": 0.0,
                    "max_posed_vertex_error": 0.0,
                    "max_posed_normal_error": 0.0,
                    "max_posed_proxy_endpoint_error": 0.0,
                },
            }
        )

    payload = {
        "projection_contract": "test-projection-v1",
        "manifest_sha256": "c" * 64,
        "manifest_bytes": 1,
        "godot_version": smoke.EXPECTED_GODOT_VERSION,
        "profile_ids": list(DEFAULTS),
        "pose_id": "test-pose",
        "pose_sha256": "d" * 64,
        "boundary": "host_only_smoke",
        "profiles": payload_profiles,
    }
    report = {
        "schema": smoke.REPORT_SCHEMA,
        "status": "success",
        "boundary": smoke.REPORT_BOUNDARY,
        "claims": deepcopy(smoke.REPORT_CLAIMS),
        "scope_flags": deepcopy(smoke.REPORT_FLAGS),
        "godot_version": smoke.EXPECTED_GODOT_VERSION,
        "godot_engine_version_string": smoke.EXPECTED_GODOT_ENGINE_VERSION_STRING,
        "profile_ids": list(DEFAULTS),
        "candidate_profile_sha256": candidate_hashes,
        "validated_gallery": {
            "projection_contract": "test-projection-v1",
            "manifest_sha256": "c" * 64,
            "manifest_bytes": 1,
            "pose_id": "test-pose",
            "pose_sha256": "d" * 64,
            "boundary": "host_only_smoke",
        },
        "artifact_hash_identities": artifact_identities,
        "coordinate_rule": {
            "kind": "disposable_host_local_identity",
            "mapping": "CK XYZ -> Godot XYZ: x->x, y->y, z->z",
            "scope": smoke.REPORT_BOUNDARY,
            "profile_translations": [list(value) for value in smoke.EXPECTED_TRANSLATIONS],
        },
        "pose_binding": {
            "pose_id": "test-pose",
            "pose_sha256": "d" * 64,
            "path": "structural_embodiment_shared_pose.json",
            "rule_count": 18,
            "rules_validated": True,
            "applied_to_skeleton3d": True,
            "ik": False,
            "contact": False,
        },
        "profiles": actual_profiles,
    }
    return payload, report


def _update_payload_artifact(payload: dict, profile_id: str, artifact_name: str, data: bytes) -> None:
    expected_path = f"{profile_id}/{artifact_name}"
    for profile in payload["profiles"]:
        if profile["profile_id"] != profile_id:
            continue
        for artifact in profile["artifacts"]:
            if artifact["path"] == expected_path:
                artifact["sha256"] = hashlib.sha256(data).hexdigest()
                artifact["bytes"] = len(data)
                return
    raise AssertionError(f"missing payload artifact {expected_path}")


def _mutate_skeleton(gallery: Path, payload: dict, profile_id: str) -> None:
    path = gallery / profile_id / "skeleton.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    value["neutral"]["bones"] = []
    data = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    path.write_bytes(data)
    _update_payload_artifact(payload, profile_id, "skeleton.json", data)


def _mutate_pose(gallery: Path, payload: dict) -> None:
    path = gallery / "structural_embodiment_shared_pose.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    value["rules"][0]["angle_degrees"] = 1.0
    data = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    path.write_bytes(data)
    payload["pose_sha256"] = hashlib.sha256(data).hexdigest()


def _godot_version_probe_command() -> list[str]:
    return [str(smoke.neutral_smoke.LAUNCHER), "--headless", "--version"]


def integration_available() -> bool:
    if os.environ.get(smoke.VISIBLE_GODOT_OPT_IN) != "1":
        return False
    if not GALLERY.is_dir() or not smoke.neutral_smoke.LAUNCHER.is_file() or not smoke.neutral_smoke.LAUNCHER.stat().st_mode & 0o111:
        return False
    if not os.environ.get("DISPLAY"):
        return False
    try:
        result = subprocess.run(
            _godot_version_probe_command(),
            capture_output=True,
            text=True,
            check=False,
            timeout=smoke.neutral_smoke.GODOT_LAUNCH_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0 and smoke.EXPECTED_GODOT_VERSION in result.stdout


class SkeletalPoseSmokeValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ck-godot-skeletal-pose-test-")
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_both_frozen_profile_pairs_are_distinct_and_accepted(self) -> None:
        self.assertEqual(smoke.neutral_smoke._validate_profile_ids(DEFAULTS), DEFAULTS)
        self.assertEqual(smoke.neutral_smoke._validate_profile_ids(ALTERNATE), ALTERNATE)
        self.assertNotEqual(set(DEFAULTS), set(ALTERNATE))

    def test_visible_x11_launch_requires_explicit_attended_opt_in(self) -> None:
        with patch.dict(os.environ, {smoke.VISIBLE_GODOT_OPT_IN: ""}):
            with self.assertRaisesRegex(smoke.SmokeError, "visible X11 Godot launch is disabled"):
                smoke._launch_godot(self.root, DEFAULTS, {})

    def test_semantic_pose_command_requires_carrier_before_launch(self) -> None:
        with patch.object(smoke, "_launch_godot", side_effect=AssertionError("Godot must not launch")):
            with self.assertRaisesRegex(smoke.SmokeError, "requires --carrier"):
                smoke.run_skeletal_pose_smoke(
                    self.root,
                    DEFAULTS,
                    self.root / "report.json",
                    None,
                    self.root / "command.json",
                )

    def test_ck_projection_requires_carrier_before_launch(self) -> None:
        with patch.object(smoke, "_launch_godot", side_effect=AssertionError("Godot must not launch")):
            with self.assertRaisesRegex(smoke.SmokeError, "CK projection requires --carrier"):
                smoke.run_skeletal_pose_smoke(
                    self.root,
                    DEFAULTS,
                    self.root / "report.json",
                    None,
                    None,
                    self.root / "projection.json",
                    self.root / "creature-kernel",
                )

    def test_ck_projection_requires_explicit_cli_path_before_launch(self) -> None:
        with patch.object(smoke, "_launch_godot", side_effect=AssertionError("Godot must not launch")):
            with self.assertRaisesRegex(smoke.SmokeError, "explicit Rust CLI path"):
                smoke.run_skeletal_pose_smoke(
                    self.root,
                    DEFAULTS,
                    self.root / "report.json",
                    self.root / "carrier.json",
                    None,
                    self.root / "projection.json",
                )

    def test_semantic_contact_command_requires_all_predecessors_before_launch(self) -> None:
        missing_predecessors = (
            (None, self.root / "pose.json", self.root / "projection.json", self.root / "cli"),
            (self.root / "carrier.json", self.root / "pose.json", None, None),
            (self.root / "carrier.json", None, self.root / "projection.json", self.root / "cli"),
            (self.root / "carrier.json", self.root / "pose.json", self.root / "projection.json", None),
        )
        for carrier_path, pose_path, projection_path, cli_path in missing_predecessors:
            with self.subTest(carrier=carrier_path, pose=pose_path, projection=projection_path, cli=cli_path):
                with patch.object(smoke, "_launch_godot", side_effect=AssertionError("Godot must not launch")):
                    with self.assertRaisesRegex(smoke.SmokeError, "requires carrier, CK projection, explicit Rust CLI, and semantic pose command"):
                        smoke.run_skeletal_pose_smoke(
                            self.root,
                            None,
                            self.root / "report.json",
                            carrier_path,
                            pose_path,
                            projection_path,
                            cli_path,
                            self.root / "contact.json",
                        )

    def test_contact_mode_mocked_launch_receives_canonical_command_and_revalidates(self) -> None:
        payload, report = _skeletal_validation_fixture()
        projection_value, projection_identity, carrier_value, records, profile_ids = _projection_fixture(payload)
        carrier_module = SimpleNamespace(
            SCHEMA=carrier.SCHEMA,
            BOUNDARY=carrier.BOUNDARY,
            _canonical_json=carrier._canonical_json,
        )
        carrier_identity = smoke._carrier_identity(carrier_value, carrier_module)
        command = {"pose": "fixture"}
        command_identity = {"sha256": "p" * 64}
        semantic_payload = {"rules": []}
        contact_command, contact_identity = _contact_command_fixture()
        serializer = lambda value: (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
        contact_module = SimpleNamespace(_canonical_json=serializer)
        carrier_result = (carrier_module, carrier_value, payload, profile_ids, tuple(record["instance_id"] for record in records))
        projection_result = (None, projection_value, projection_identity)
        pose_result = (semantic_command, command, command_identity, semantic_payload)
        contact_result = (contact_module, contact_command, contact_identity)
        with (
            patch.object(smoke, "_validated_carrier_input", side_effect=[carrier_result, carrier_result]),
            patch.object(smoke, "_validated_projection_input", side_effect=[projection_result, projection_result]),
            patch.object(smoke, "_validated_semantic_pose_command", side_effect=[pose_result, pose_result]),
            patch.object(smoke, "_validated_semantic_contact_command", side_effect=[contact_result, contact_result]) as validate_contact,
            patch.object(smoke, "_load_contact_command_module", return_value=contact_module),
            patch.object(smoke, "_launch_godot", return_value=("", "", 0, report)) as launch,
            patch.object(smoke, "_validate_report") as validate_report,
            patch.object(smoke.neutral_smoke, "_publish_report") as publish,
        ):
            result = smoke.run_skeletal_pose_smoke(
                self.root,
                None,
                self.root / "report.json",
                self.root / "carrier.json",
                self.root / "pose.json",
                self.root / "projection.json",
                self.root / "creature-kernel",
                self.root / "contact.json",
            )
        self.assertIs(result, report)
        self.assertEqual(validate_contact.call_count, 2)
        self.assertEqual(launch.call_args.args[10], contact_command)
        self.assertEqual(launch.call_args.args[11], contact_identity)
        self.assertEqual(launch.call_args.args[12], self.root / "creature-kernel")
        validate_report.assert_called_once_with(
            report,
            payload,
            profile_ids,
            carrier_identity,
            smoke._carrier_avatar_records(carrier_value),
            command,
            command_identity,
            projection_value,
            projection_identity,
            contact_command,
            contact_identity,
        )
        publish.assert_called_once_with(self.root / "report.json", report)

    def test_contact_report_requires_runtime_mapping_impulse_response_and_exact_snapshots(self) -> None:
        command, identity = _contact_command_fixture()
        evidence = _contact_report_fixture(command, identity)
        smoke._validate_contact_report({"semantic_contact": evidence}, command, identity)

        def clear_contact_counts(value: dict) -> None:
            for record in value["contact_tick_evidence"]:
                record["contact_count"] = 0

        mutations = {
            "swapped participants": lambda value: value["participants"].reverse(),
            "aggregate mapping": lambda value: value.__setitem__("participants", []),
            "echoed impulse": lambda value: value["solver_impulses"][0].__setitem__("runtime_derived", False),
            "zero impulse": lambda value: value["solver_impulses"][0].__setitem__("impulse_magnitude", 0.0),
            "solver scalar mismatch": lambda value: value["solver_impulses"][0].__setitem__("impulse_magnitude", 0.3),
            "top-level solver scalar path": lambda value: value.__setitem__("solver_impulse", 0.25),
            "solver impulse scalar alias": lambda value: (
                value["solver_impulses"][0].__setitem__("solver_impulse", value["solver_impulses"][0].pop("impulse_magnitude"))
            ),
            "solver provenance alias": lambda value: (
                value["solver_impulses"][0].__setitem__("derived_from_runtime", value["solver_impulses"][0].pop("runtime_derived"))
            ),
            "contact events alias": lambda value: value.__setitem__("contact_events", ["enter", "contact", "exit"]),
            "reordered phases": lambda value: value.__setitem__("phase_order", list(reversed(smoke.CONTACT_PHASE_ORDER))),
            "nonfinite response": lambda value: value["response"].__setitem__("displacement", float("inf")),
            "reported normal velocity mismatch": lambda value: value["response"].__setitem__("normal_velocity_delta", 0.2),
            "reported normal displacement mismatch": lambda value: value["response"].__setitem__("normal_displacement", 0.2),
            "reported displacement mismatch": lambda value: value["response"].__setitem__("displacement", 0.2),
            "velocity snapshot mismatch": lambda value: value["response"]["snapshots"]["contact"].__setitem__("linear_velocity", [0.2, 0.0, 0.0]),
            "transform snapshot mismatch": lambda value: value["response"]["snapshots"]["final"]["transform"].__setitem__(3, 0.2),
            "position snapshot mismatch": lambda value: value["response"]["snapshots"]["final"]["position"].__setitem__(0, 0.2),
            "snapshot label mismatch": lambda value: value["response"]["snapshots"]["contact"].__setitem__("label", "initial"),
            "snapshot tick mismatch": lambda value: value["response"]["snapshots"]["contact"].__setitem__("tick", 24),
            "snapshot differs from strongest contact tick": lambda value: value["response"]["snapshots"]["contact"].__setitem__("tick", 26),
            "nonzero initial velocity": lambda value: value["response"]["snapshots"]["initial"].__setitem__("linear_velocity", [0.1, 0.0, 0.0]),
            "locked rotation violated": lambda value: value["response"]["snapshots"]["contact"].__setitem__("angular_velocity", [0.0, 0.1, 0.0]),
            "strongest sample normal mismatch": lambda value: value["response"].__setitem__("normal", [0.0, 1.0, 0.0]),
            "response magnitude alias": lambda value: (
                value["response"].__setitem__("normal_velocity_change", value["response"].pop("normal_velocity_delta"))
            ),
            "missing contact tick": lambda value: value["contact_tick_evidence"].pop(),
            "setup contact count": lambda value: value["contact_tick_evidence"][0].__setitem__("contact_count", 1),
            "reordered contact tick": lambda value: value["contact_tick_evidence"][1].__setitem__("tick", 2),
            "wrong contact tick phase": lambda value: value["contact_tick_evidence"][25].__setitem__("phase", "approach"),
            "negative contact count": lambda value: value["contact_tick_evidence"][25].__setitem__("contact_count", -1),
            "constant events without transitions": clear_contact_counts,
            "final exit contact count": lambda value: value["contact_tick_evidence"][-1].__setitem__("contact_count", 1),
            "sample tick outside trace": lambda value: value["solver_impulses"][0]["contact_samples"][0].__setitem__("tick", smoke.CONTACT_TOTAL_TICKS + 1),
            "sample phase disagrees with trace": lambda value: value["solver_impulses"][0]["contact_samples"][0].__setitem__("phase", "release"),
            "sample index exceeds trace count": lambda value: value["solver_impulses"][0]["contact_samples"][0].__setitem__("contact_index", 1),
            "wrong response mass": lambda value: value["physics_configuration"].__setitem__("response_mass", 2.0),
            "boolean response mass": lambda value: value["physics_configuration"].__setitem__("response_mass", True),
            "wrong response gravity": lambda value: value["physics_configuration"].__setitem__("response_gravity_scale", 0.1),
            "boolean response gravity": lambda value: value["physics_configuration"].__setitem__("response_gravity_scale", False),
            "sleep enabled": lambda value: value["physics_configuration"].__setitem__("response_can_sleep", True),
            "sleep evidence omitted": lambda value: value["physics_configuration"].pop("response_can_sleep"),
            "wrong physics backend": lambda value: value["physics_configuration"].__setitem__("physics_engine", "DEFAULT"),
        }
        for name, mutate in mutations.items():
            with self.subTest(mutation=name):
                mutated = deepcopy(evidence)
                mutate(mutated)
                with self.assertRaises(smoke.SmokeError):
                    smoke._validate_contact_report({"semantic_contact": mutated}, command, identity)

        for alias in ("semantic_contact_evidence", "contact_evidence", "semantic_contact_response"):
            with self.subTest(report_alias=alias):
                report = {"semantic_contact": deepcopy(evidence), alias: deepcopy(evidence)}
                with self.assertRaises(smoke.SmokeError):
                    smoke._validate_contact_report(report, command, identity)

    def test_deformation_report_requires_exact_scope_schema_and_independent_vertex_evidence(self) -> None:
        payload, report, command, identity, captures = _deformation_report_fixture()
        smoke._validate_report(
            report,
            payload,
            DEFAULTS,
            semantic_contact_command=command,
            contact_command_identity=identity,
            deformation_capture_bytes=captures,
        )

        mutations = {
            "wrong boundary": lambda value: value.__setitem__("boundary", smoke.CONTACT_REPORT_BOUNDARY),
            "extra claim": lambda value: value["claims"].append("unbounded deformation"),
            "deformation flag disabled": lambda value: value["scope_flags"].__setitem__("deformation", False),
            "missing deformation field": lambda value: value["semantic_deformation"].pop("drive"),
            "reference geometry tampered": lambda value: value["semantic_deformation"]["states"]["reference"]["vertices"][1].__setitem__(0, 0.1),
            "peak residual tampered": lambda value: value["semantic_deformation"]["states"]["peak"]["vertices"][1].__setitem__(0, 0.1),
            "falloff weight tampered": _remove_first_positive_falloff_weight,
            "falloff radius ratio tampered": lambda value: value["semantic_deformation"]["drive"].__setitem__("falloff_radius_ratio", 0.75),
            "unit falloff peak removed": lambda value: _scale_reported_deformation_falloff(value, 0.8),
            "recovered vertex tampered": lambda value: value["semantic_deformation"]["states"]["recovered"]["vertices"][1].__setitem__(1, 0.1),
            "outside falloff metric tampered": lambda value: value["semantic_deformation"]["states"]["peak"].__setitem__("outside_falloff_max_residual", 0.1),
            "peak tick detached": lambda value: value["semantic_deformation"]["drive"].__setitem__("peak_tick", 26),
            "runtime contact point detached": lambda value: value["semantic_deformation"]["drive"].__setitem__("runtime_contact_point", [0.26, 0.0, 0.0]),
            "body-local contact point detached": lambda value: value["semantic_deformation"]["drive"].__setitem__("local_contact_point", [0.21, 0.0, 0.0]),
            "sample response transform detached": lambda value: value["semantic_deformation"]["drive"]["sample_response_transform"].__setitem__(3, 0.06),
            "inward direction leaves contact-normal line": lambda value: value["semantic_deformation"]["drive"].__setitem__("local_inward_direction", [0.0, 1.0, 0.0]),
            "inward direction points outward": lambda value: value["semantic_deformation"]["drive"].__setitem__("local_inward_direction", [1.0, 0.0, 0.0]),
            "capture digest tampered": lambda value: value["semantic_deformation"]["captures"][0].__setitem__("sha256", "0" * 64),
        }
        for name, mutate in mutations.items():
            with self.subTest(mutation=name):
                mutated_report = deepcopy(report)
                mutated_captures = dict(captures)
                mutate(mutated_report)
                with self.assertRaises(smoke.SmokeError):
                    smoke._validate_report(
                        mutated_report,
                        payload,
                        DEFAULTS,
                        semantic_contact_command=command,
                        contact_command_identity=identity,
                        deformation_capture_bytes=mutated_captures,
                    )

        tampered_captures = dict(captures)
        tampered_captures["peak.png"] = tampered_captures["peak.png"][:-1] + b"!"
        with self.assertRaises(smoke.SmokeError):
            smoke._validate_report(
                report,
                payload,
                DEFAULTS,
                semantic_contact_command=command,
                contact_command_identity=identity,
                deformation_capture_bytes=tampered_captures,
            )

    def test_deformation_inward_direction_accepts_either_contact_normal_convention(self) -> None:
        payload, report, command, identity, captures = _deformation_report_fixture()
        flipped = deepcopy(report)
        sample = flipped["semantic_contact"]["solver_impulses"][0]["contact_samples"][0]
        sample["normal"] = [-1.0, 0.0, 0.0]
        flipped["semantic_contact"]["response"]["normal"] = [-1.0, 0.0, 0.0]
        smoke._validate_report(
            flipped,
            payload,
            DEFAULTS,
            semantic_contact_command=command,
            contact_command_identity=identity,
            deformation_capture_bytes=captures,
        )

    def test_deformation_captures_require_real_nonuniform_pixels_and_bounded_change(self) -> None:
        _payload, report, _command, _identity, captures = _deformation_report_fixture()
        smoke._validate_deformation_captures(_capture_evidence_for_bytes(report, captures), captures)

        blank = {file_name: _png_fixture(blank=True) for file_name in smoke.DEFORMATION_CAPTURE_NAMES}
        identical = dict(captures)
        identical["peak.png"] = identical["reference.png"]
        trivial = dict(captures)
        trivial["peak.png"] = _one_pixel_delta(trivial["reference.png"])
        with Image.open(BytesIO(captures["reference.png"])) as source:
            inverted_image = ImageOps.invert(source.convert("RGB")).convert("RGBA")
        overly_broad = dict(captures)
        overly_broad["peak.png"] = _encode_png(inverted_image)

        cases = (
            ("blank", blank, "blank or uniform.*observed_unique_rgba_pixels=1"),
            ("identical", identical, "bounded meaningful.*observed_changed_pixels=0"),
            ("trivial", trivial, "bounded meaningful.*observed_changed_pixels=1"),
            ("overly broad", overly_broad, "bounded meaningful.*observed_changed_pixel_fraction="),
        )
        for name, mutated, expected in cases:
            with self.subTest(capture=name):
                with self.assertRaisesRegex(smoke.SmokeError, expected):
                    smoke._validate_deformation_captures(_capture_evidence_for_bytes(report, mutated), mutated)

    def test_deformation_capture_destination_requires_full_contact_inputs(self) -> None:
        input_sets = (
            (None, self.root / "pose.json", self.root / "projection.json", self.root / "cli", self.root / "contact.json"),
            (self.root / "carrier.json", None, self.root / "projection.json", self.root / "cli", self.root / "contact.json"),
            (self.root / "carrier.json", self.root / "pose.json", None, None, self.root / "contact.json"),
            (self.root / "carrier.json", self.root / "pose.json", self.root / "projection.json", self.root / "cli", None),
        )
        for carrier_path, pose_path, projection_path, cli_path, contact_path in input_sets:
            with self.subTest(carrier=carrier_path, pose=pose_path, projection=projection_path, contact=contact_path):
                with patch.object(smoke, "_launch_godot", side_effect=AssertionError("Godot must not launch")):
                    with self.assertRaisesRegex(smoke.SmokeError, "require.*full semantic-contact predecessor"):
                        smoke.run_skeletal_pose_smoke(
                            self.root,
                            None,
                            self.root / "report.json",
                            carrier_path,
                            pose_path,
                            projection_path,
                            cli_path,
                            contact_path,
                            self.root / "captures",
                        )

    def test_deformation_capture_directory_is_not_published_when_report_validation_fails(self) -> None:
        payload, report, contact_command, contact_identity, captures = _deformation_report_fixture()
        projection_value, projection_identity, carrier_value, records, profile_ids = _projection_fixture(payload)
        carrier_module = SimpleNamespace(
            SCHEMA=carrier.SCHEMA,
            BOUNDARY=carrier.BOUNDARY,
            _canonical_json=carrier._canonical_json,
        )
        carrier_result = (
            carrier_module,
            carrier_value,
            payload,
            profile_ids,
            tuple(record["instance_id"] for record in records),
        )
        projection_result = (None, projection_value, projection_identity)
        pose_command = {"pose": "fixture"}
        pose_identity = {"sha256": "p" * 64}
        pose_result = (semantic_command, pose_command, pose_identity, {"rules": []})
        contact_module = SimpleNamespace(
            _canonical_json=lambda value: (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
        )
        contact_result = (contact_module, contact_command, contact_identity)

        def launch(*_args, **kwargs):
            kwargs["deformation_capture_sink"](captures)
            return "", "", 0, report

        capture_path = self.root / "captures"
        report_path = self.root / "report.json"
        with (
            patch.object(smoke, "_validated_carrier_input", return_value=carrier_result),
            patch.object(smoke, "_validated_projection_input", return_value=projection_result),
            patch.object(smoke, "_validated_semantic_pose_command", return_value=pose_result),
            patch.object(smoke, "_validated_semantic_contact_command", return_value=contact_result),
            patch.object(smoke, "_launch_godot", side_effect=launch),
            patch.object(smoke, "_validate_report", side_effect=smoke.SmokeError("invalid report")),
            patch.object(smoke.neutral_smoke, "_publish_report") as publish_report,
            patch.object(smoke, "_publish_deformation_captures") as publish_captures,
        ):
            with self.assertRaisesRegex(smoke.SmokeError, "invalid report"):
                smoke.run_skeletal_pose_smoke(
                    self.root,
                    None,
                    report_path,
                    self.root / "carrier.json",
                    self.root / "pose.json",
                    self.root / "projection.json",
                    self.root / "creature-kernel",
                    self.root / "contact.json",
                    capture_path,
                )

        self.assertFalse(capture_path.exists())
        self.assertFalse(report_path.exists())
        publish_report.assert_not_called()
        publish_captures.assert_not_called()

    def test_deformation_capture_directory_is_not_published_when_postflight_predecessor_revalidation_fails(self) -> None:
        payload, report, contact_command, contact_identity, captures = _deformation_report_fixture()
        projection_value, projection_identity, carrier_value, records, profile_ids = _projection_fixture(payload)
        carrier_module = SimpleNamespace(
            SCHEMA=carrier.SCHEMA,
            BOUNDARY=carrier.BOUNDARY,
            _canonical_json=carrier._canonical_json,
        )
        carrier_result = (
            carrier_module,
            carrier_value,
            payload,
            profile_ids,
            tuple(record["instance_id"] for record in records),
        )
        projection_result = (None, projection_value, projection_identity)
        pose_command = {"pose": "fixture"}
        pose_identity = {"sha256": "p" * 64}
        pose_result = (semantic_command, pose_command, pose_identity, {"rules": []})
        contact_module = SimpleNamespace(
            _canonical_json=lambda value: (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
        )
        contact_result = (contact_module, contact_command, contact_identity)

        def launch(*_args, **kwargs):
            kwargs["deformation_capture_sink"](captures)
            return "", "", 0, report

        capture_path = self.root / "captures"
        report_path = self.root / "report.json"
        with (
            patch.object(smoke, "_validated_carrier_input", side_effect=[carrier_result, carrier_result]),
            patch.object(smoke, "_validated_projection_input", side_effect=[projection_result, projection_result]),
            patch.object(smoke, "_validated_semantic_pose_command", side_effect=[pose_result, pose_result]),
            patch.object(
                smoke,
                "_validated_semantic_contact_command",
                side_effect=[contact_result, smoke.SmokeError("postflight predecessor revalidation failed")],
            ),
            patch.object(smoke, "_launch_godot", side_effect=launch),
            patch.object(smoke, "_validate_report"),
            patch.object(smoke.neutral_smoke, "_publish_report") as publish_report,
            patch.object(smoke, "_publish_deformation_captures") as publish_captures,
        ):
            with self.assertRaisesRegex(smoke.SmokeError, "postflight predecessor revalidation failed"):
                smoke.run_skeletal_pose_smoke(
                    self.root,
                    None,
                    report_path,
                    self.root / "carrier.json",
                    self.root / "pose.json",
                    self.root / "projection.json",
                    self.root / "creature-kernel",
                    self.root / "contact.json",
                    capture_path,
                )

        self.assertFalse(capture_path.exists())
        self.assertFalse(report_path.exists())
        self.assertEqual(list(self.root.iterdir()), [])
        publish_report.assert_not_called()
        publish_captures.assert_not_called()

    def test_deformation_capture_publication_failure_precedes_success_report(self) -> None:
        _payload, report, _command, _identity, captures = _deformation_report_fixture()
        capture_path = self.root / "captures"
        report_path = self.root / "report.json"
        with (
            patch.object(
                smoke,
                "_publish_deformation_captures",
                side_effect=smoke.SmokeError("capture publication failed"),
            ) as publish_captures,
            patch.object(smoke.neutral_smoke, "_publish_report") as publish_report,
        ):
            with self.assertRaisesRegex(smoke.SmokeError, "capture publication failed"):
                smoke._publish_deformation_result(report_path, report, capture_path, captures)
        publish_captures.assert_called_once_with(capture_path, captures)
        publish_report.assert_not_called()
        self.assertFalse(capture_path.exists())
        self.assertFalse(report_path.exists())

    def test_deformation_report_publication_failure_rolls_back_exact_capture_set(self) -> None:
        _payload, report, _command, _identity, captures = _deformation_report_fixture()
        capture_path = self.root / "captures"
        report_path = self.root / "report.json"
        with patch.object(
            smoke.neutral_smoke,
            "_publish_report",
            side_effect=smoke.SmokeError("report publication failed"),
        ) as publish_report:
            with self.assertRaisesRegex(smoke.SmokeError, "report publication failed"):
                smoke._publish_deformation_result(report_path, report, capture_path, captures)
        publish_report.assert_called_once_with(report_path, report)
        self.assertFalse(capture_path.exists())
        self.assertFalse(report_path.exists())
        self.assertEqual(list(self.root.iterdir()), [])

    def test_deformation_capture_publication_is_atomic_no_overwrite_and_exact(self) -> None:
        _payload, _report, _command, _identity, captures = _deformation_report_fixture()
        capture_path = self.root / "captures"

        smoke._publish_deformation_captures(capture_path, captures)

        self.assertEqual(
            {entry.name for entry in capture_path.iterdir()},
            set(smoke.DEFORMATION_CAPTURE_NAMES),
        )
        for file_name in smoke.DEFORMATION_CAPTURE_NAMES:
            self.assertEqual((capture_path / file_name).read_bytes(), captures[file_name])
        self.assertEqual({entry.name for entry in self.root.iterdir()}, {capture_path.name})

        before = {
            entry.name: entry.read_bytes()
            for entry in capture_path.iterdir()
        }
        with self.assertRaisesRegex(smoke.SmokeError, "must not already exist"):
            smoke._publish_deformation_captures(capture_path, captures)
        after = {
            entry.name: entry.read_bytes()
            for entry in capture_path.iterdir()
        }
        self.assertEqual(after, before)
        self.assertEqual({entry.name for entry in self.root.iterdir()}, {capture_path.name})

    def test_contact_command_module_exposes_exact_runner_api(self) -> None:
        module = smoke._load_contact_command_module()
        self.assertTrue(callable(module.load_contact_command))
        self.assertTrue(callable(module.validate_contact_command))
        self.assertTrue(callable(module.command_identity))
        self.assertFalse(hasattr(module, "contact_command_identity"))

    def test_no_contact_report_rejects_contact_evidence_aliases(self) -> None:
        payload, report = _skeletal_validation_fixture()
        for alias in ("semantic_contact", "semantic_contact_evidence", "contact_evidence"):
            with self.subTest(report_alias=alias):
                mutated = deepcopy(report)
                mutated[alias] = {}
                with self.assertRaisesRegex(smoke.SmokeError, "unexpected semantic contact evidence"):
                    smoke._validate_report(mutated, payload, DEFAULTS)

    def test_ck_projection_cross_checks_fresh_carrier_payload_and_tampering(self) -> None:
        payload, _report = _skeletal_validation_fixture()
        projection_value, identity, carrier_value, records, profile_ids = _projection_fixture(payload)
        carrier_module = SimpleNamespace(
            SCHEMA=carrier.SCHEMA,
            BOUNDARY=carrier.BOUNDARY,
            _canonical_json=lambda value: (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode(),
        )
        carrier_identity = smoke._carrier_identity(carrier_value, carrier_module)
        projection_module = SimpleNamespace(
            ProjectionError=ValueError,
            validate_projection=lambda *_args, **_kwargs: projection_value,
            projection_identity=lambda _value: identity,
        )
        with patch.object(smoke, "_load_projection_module", return_value=projection_module):
            result = smoke._validated_projection_input(
                self.root,
                self.root / "carrier.json",
                carrier_value,
                {**payload, "profiles": [{**profile, "artifacts": projection_value["avatars"][index]["artifacts"]} for index, profile in enumerate(payload["profiles"])]},
                profile_ids,
                tuple(record["instance_id"] for record in records),
                carrier_identity,
                records,
                self.root / "projection.json",
                self.root / "creature-kernel",
            )
        self.assertIs(result[1], projection_value)
        self.assertIs(result[2], identity)

        tampered = deepcopy(projection_value)
        tampered["avatars"][0]["artifacts"] = []
        with patch.object(
            smoke,
            "_load_projection_module",
            return_value=SimpleNamespace(
                ProjectionError=ValueError,
                validate_projection=lambda *_args, **_kwargs: tampered,
                projection_identity=lambda _value: identity,
            ),
        ):
            with self.assertRaisesRegex(smoke.SmokeError, "artifacts disagree"):
                smoke._validated_projection_input(
                    self.root,
                    self.root / "carrier.json",
                    carrier_value,
                    {**payload, "profiles": [{**profile, "artifacts": projection_value["avatars"][index]["artifacts"]} for index, profile in enumerate(payload["profiles"])]},
                    profile_ids,
                    tuple(record["instance_id"] for record in records),
                    carrier_identity,
                    records,
                    self.root / "projection.json",
                    self.root / "creature-kernel",
                )

    def test_report_rejects_projection_fields_without_projection_mode(self) -> None:
        payload, report = _skeletal_validation_fixture()
        report["validated_ck_projection"] = {"unexpected": True}
        with self.assertRaisesRegex(smoke.SmokeError, "unexpected CK projection identity"):
            smoke._validate_report(report, payload, DEFAULTS)

        payload, report = _skeletal_validation_fixture()
        report["profiles"][0]["ck_projection_binding"] = {}
        with self.assertRaisesRegex(smoke.SmokeError, "unexpected CK projection binding"):
            smoke._validate_report(report, payload, DEFAULTS)

    def test_projection_report_fields_are_exactly_validated(self) -> None:
        payload, report = _skeletal_validation_fixture()
        projection_value, identity, _carrier_value, _records, _profile_ids = _projection_fixture(payload)
        report["validated_ck_projection"] = deepcopy(identity)
        bindings = smoke._projection_bindings(projection_value)
        for index, binding in enumerate(bindings):
            report["profiles"][index]["ck_projection_binding"] = deepcopy(binding)
        smoke._validate_report(report, payload, DEFAULTS, projection=projection_value, projection_identity=identity)
        report["profiles"][0]["ck_projection_binding"]["source"]["bytes"] = 2
        with self.assertRaisesRegex(smoke.SmokeError, "CK projection binding is invalid"):
            smoke._validate_report(report, payload, DEFAULTS, projection=projection_value, projection_identity=identity)

    def test_projection_postflight_change_fails_before_publication(self) -> None:
        payload, report = _skeletal_validation_fixture()
        projection_value, identity, carrier_value, records, profile_ids = _projection_fixture(payload)
        carrier_module = SimpleNamespace(
            SCHEMA=carrier.SCHEMA,
            BOUNDARY=carrier.BOUNDARY,
            _canonical_json=lambda value: (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode(),
        )
        validated = (carrier_module, carrier_value, payload, profile_ids, tuple(record["instance_id"] for record in records))
        changed = deepcopy(projection_value)
        changed["avatars"][0]["label"] = "changed-after-launch"
        with (
            patch.object(smoke, "_validated_carrier_input", side_effect=[validated, validated]),
            patch.object(smoke, "_validated_projection_input", side_effect=[(None, projection_value, identity), (None, changed, identity)]),
            patch.object(smoke, "_launch_godot", return_value=("", "", 0, report)),
            patch.object(smoke, "_validate_report"),
            patch.object(smoke.neutral_smoke, "_publish_report") as publish,
        ):
            with self.assertRaisesRegex(smoke.SmokeError, "CK projection changed"):
                smoke.run_skeletal_pose_smoke(
                    self.root,
                    None,
                    self.root / "report.json",
                    self.root / "carrier.json",
                    None,
                    self.root / "projection.json",
                    self.root / "creature-kernel",
                )
        publish.assert_not_called()

    def test_projection_and_semantic_command_transport_uses_exact_json_arguments(self) -> None:
        payload, _report = _skeletal_validation_fixture()
        projection_value, projection_identity, _carrier_value, records, profile_ids = _projection_fixture(payload)
        carrier_identity = deepcopy(CARRIER_IDENTITY)
        command = {"command": "fixture"}
        command_identity = {"sha256": "c" * 64}
        semantic_payload = {"rules": []}
        serializer = lambda value: (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
        command_module = SimpleNamespace(_canonical_json=serializer)
        projection_module = SimpleNamespace(_canonical_json=serializer)
        contact_command, contact_identity = _contact_command_fixture()
        contact_module = SimpleNamespace(_canonical_json=serializer)
        with tempfile.TemporaryDirectory(prefix="ck-godot-projection-args-") as temporary:
            root = Path(temporary)
            project_file = root / "project.godot"
            script_file = root / "skeletal_pose_smoke.gd"
            launcher = root / "godot-launcher"
            project_file.write_text("[application]\n", encoding="utf-8")
            script_file.write_text("extends SceneTree\n", encoding="utf-8")
            launcher.write_text("", encoding="utf-8")
            launcher.chmod(0o755)
            with (
                patch.object(smoke.neutral_smoke, "PROJECT_FILE", project_file),
                patch.object(smoke, "GODOT_SCRIPT", script_file),
                patch.object(smoke.neutral_smoke, "LAUNCHER", launcher),
                patch.object(smoke.neutral_smoke, "_resolve_pinned_binary", return_value=launcher),
                patch.object(smoke, "_load_command_module", return_value=command_module),
                patch.object(smoke, "_load_projection_module", return_value=projection_module),
                patch.object(smoke, "_load_contact_command_module", return_value=contact_module),
                patch.object(smoke.neutral_smoke, "_read_report", return_value={}),
                patch.object(smoke.neutral_smoke, "_has_godot_error_diagnostics", return_value=False),
                patch.dict(os.environ, {smoke.VISIBLE_GODOT_OPT_IN: "1"}),
                patch.object(subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "", "")) as run,
            ):
                smoke._launch_godot(
                    self.root,
                    profile_ids,
                    payload,
                    carrier_identity,
                    records,
                    command,
                    command_identity,
                    semantic_payload,
                    projection_value,
                    projection_identity,
                    contact_command,
                    contact_identity,
                    self.root / "creature-kernel",
                )
        command_line = run.call_args.args[0]
        self.assertEqual(
            command_line[command_line.index("--ck-projection-json") + 1],
            serializer(projection_value).decode().removesuffix("\n"),
        )
        self.assertEqual(
            command_line[command_line.index("--ck-projection-identity-json") + 1],
            serializer(projection_identity).decode().removesuffix("\n"),
        )
        self.assertNotIn("\n", command_line[command_line.index("--ck-projection-json") + 1])
        self.assertEqual(
            command_line[command_line.index("--semantic-contact-command-json") + 1],
            serializer(contact_command).decode().removesuffix("\n"),
        )
        self.assertEqual(
            command_line[command_line.index("--semantic-contact-command-identity-json") + 1],
            serializer(contact_identity).decode().removesuffix("\n"),
        )
        self.assertNotIn("\n", command_line[command_line.index("--semantic-contact-command-json") + 1])

    def test_integration_availability_probe_times_out_fail_closed(self) -> None:
        with (
            patch.object(sys.modules[__name__], "GALLERY", self.root),
            patch.object(smoke.neutral_smoke, "LAUNCHER", Path(sys.executable)),
            patch.dict(os.environ, {smoke.VISIBLE_GODOT_OPT_IN: "1", "DISPLAY": ":99"}),
            patch.object(subprocess, "run", side_effect=subprocess.TimeoutExpired([sys.executable], 1)),
        ):
            self.assertFalse(integration_available())

    def test_availability_version_probe_is_explicitly_headless(self) -> None:
        launcher = self.root / "fake-godot"
        with patch.object(smoke.neutral_smoke, "LAUNCHER", launcher):
            self.assertEqual(
                _godot_version_probe_command(),
                [str(launcher), "--headless", "--version"],
            )
        source = HERE.read_text(encoding="utf-8")
        self.assertIn("result = subprocess.run(", source)
        self.assertIn("timeout=smoke.neutral_smoke.GODOT_LAUNCH_TIMEOUT_SECONDS", source)

    def test_headless_script_compile_reaches_fail_closed_projection_diagnostic(self) -> None:
        launcher = smoke.neutral_smoke.LAUNCHER
        if not launcher.is_file() or not os.access(launcher, os.X_OK):
            self.skipTest(f"exact pinned Godot launcher unavailable: {launcher}")
        try:
            pinned_binary = smoke.neutral_smoke._resolve_pinned_binary()
        except smoke.SmokeError as exc:
            self.skipTest(f"exact pinned Godot binary unavailable: {exc}")
        if not pinned_binary.is_file() or not os.access(pinned_binary, os.X_OK):
            self.skipTest(f"exact pinned Godot binary unavailable: {pinned_binary}")

        project_root = self.root / "headless-project"
        project_root.mkdir()
        project_file = project_root / smoke.neutral_smoke.PROJECT_FILE.name
        script_file = project_root / smoke.GODOT_SCRIPT.name
        report_file = project_root / "unexpected-report.json"
        shutil.copyfile(smoke.neutral_smoke.PROJECT_FILE, project_file)
        shutil.copyfile(smoke.GODOT_SCRIPT, script_file)

        isolated_root = self.root / "isolated-runtime"
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
        isolated_paths["XDG_RUNTIME_DIR"].chmod(0o700)

        environment = os.environ.copy()
        environment.update({key: str(value) for key, value in isolated_paths.items()})
        environment["CK_GODOT_4_7_2_BINARY"] = str(pinned_binary)
        environment.pop(smoke.VISIBLE_GODOT_OPT_IN, None)
        environment.pop("DISPLAY", None)
        environment.pop("WAYLAND_DISPLAY", None)
        self.assertNotIn(smoke.VISIBLE_GODOT_OPT_IN, environment)

        command = [
            str(launcher),
            "--headless",
            "--audio-driver",
            "Dummy",
            "--path",
            str(project_root),
            "--script",
            str(script_file),
            "--",
            "--gallery",
            str(self.root / "intentionally-missing-gallery"),
            "--profile-id",
            DEFAULTS[0],
            "--profile-id",
            DEFAULTS[1],
            "--report",
            str(report_file),
            "--validated-json",
            "{}",
        ]
        self.assertEqual(command[1], "--headless")
        self.assertEqual(environment["CK_GODOT_4_7_2_BINARY"], str(pinned_binary))

        def repository_godot_snapshot() -> dict[Path, tuple[str, str]]:
            snapshot = {}
            for godot_root in REPOSITORY_ROOT.rglob(".godot"):
                if not godot_root.is_dir():
                    continue
                for path in (godot_root, *godot_root.rglob("*")):
                    relative = path.relative_to(REPOSITORY_ROOT)
                    if path.is_symlink():
                        snapshot[relative] = ("symlink", os.readlink(path))
                    elif path.is_file():
                        snapshot[relative] = ("file", hashlib.sha256(path.read_bytes()).hexdigest())
                    elif path.is_dir():
                        snapshot[relative] = ("directory", "")
                    else:
                        snapshot[relative] = ("other", "")
            return snapshot

        before_godot_cache = repository_godot_snapshot()
        try:
            completed = subprocess.run(
                command,
                cwd=project_root,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
                timeout=smoke.neutral_smoke.GODOT_LAUNCH_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            self.fail(
                f"headless Godot compile check timed out; stdout={exc.stdout!r}; stderr={exc.stderr!r}"
            )
        except OSError as exc:
            self.fail(f"headless Godot compile check could not run: {type(exc).__name__}: {exc}")
        after_godot_cache = repository_godot_snapshot()
        self.assertEqual(before_godot_cache, after_godot_cache)

        if completed.returncode == 78 and "Godot 4.7.2 preflight failed:" in completed.stderr:
            self.skipTest(f"exact pinned Godot binary unavailable: {completed.stderr.strip()}")

        diagnostics = f"stdout={completed.stdout!r}; stderr={completed.stderr!r}"
        combined_output = f"{completed.stdout}\n{completed.stderr}"
        self.assertEqual(completed.returncode, 1, f"expected fail-closed exit status 1; {diagnostics}")
        self.assertIn(FAIL_CLOSED_PROJECTION_DIAGNOSTIC, combined_output, diagnostics)
        self.assertFalse(report_file.exists(), f"invalid projection unexpectedly produced {report_file}")
        for forbidden_diagnostic in (
            "SCRIPT ERROR:",
            "SCRIPT WARNING:",
            "Parse Error:",
            "Parser Error:",
            "Warning treated as error",
            "Failed to load script",
        ):
            self.assertNotIn(forbidden_diagnostic.casefold(), combined_output.casefold(), diagnostics)
        unexpected_error_lines = [
            line
            for line in combined_output.splitlines()
            if line.lstrip().startswith(("ERROR:", "WARNING:"))
            and FAIL_CLOSED_PROJECTION_DIAGNOSTIC not in line
        ]
        self.assertEqual(unexpected_error_lines, [], diagnostics)

    def test_report_runtime_evidence_is_read_back_not_self_asserted(self) -> None:
        source = (EXPERIMENT / "skeletal_pose_smoke.gd").read_text(encoding="utf-8")
        run_source = source[source.index("func _run_smoke"):source.index("func _parse_arguments")]
        report_source = source[source.index("func _build_report"):source.index("func _parse_ply")]
        binding_source = source[source.index("func _readback_binding"):source.index("func _readback_node_counts")]
        node_source = source[source.index("func _readback_node_counts"):source.index("func _count_profile_nodes")]
        proxy_source = source[source.index("func _build_host_proxies"):source.index("func _read_proxy_geometry")]
        self.assertIn("if report.is_empty():", run_source)
        self.assertIn("runtime evidence report is empty", run_source)
        self.assertIn(
            'var binding := _readback_binding(profile, options.has("semantic_pose_command"))',
            report_source,
        )
        self.assertIn(
            "not validate_command_rotation or command_rotation_error <= RUNTIME_POSE_QUATERNION_TOLERANCE",
            binding_source,
        )
        self.assertIn(
            "_quaternion_error(quaternion, expected_quaternion) > POSE_QUATERNION_TOLERANCE",
            source,
        )
        self.assertIn("var node_counts := _readback_node_counts(profile)", report_source)
        self.assertIn("var orientation = _basis_for_y_axis", proxy_source)
        self.assertNotIn("Quaternion(Vector3.UP", proxy_source)
        self.assertIn("runtime pose rotation read-back is missing selector", binding_source)
        self.assertNotIn("force_update_all_bone_transforms", source)
        self.assertNotIn("NOTIFICATION_UPDATE_SKELETON", source)
        self.assertIn("skeleton_updated.connect", source)
        self.assertIn("--carrier-identity-json", source)
        self.assertIn("--carrier-avatar-records-json", source)
        self.assertIn("func _validate_carrier_identity", source)
        self.assertIn("func _validate_carrier_avatar_records", source)
        self.assertIn("func _readback_carrier_avatar_binding", source)
        self.assertIn("root.set_meta", source)
        self.assertIn("root.get_meta", source)
        for field in (
            "unique_bone_names",
            "parent_links_match",
            "neutral_rest_matches_published",
            "skin_bind_poses_match_published",
            "neutral_baked_mesh_matches",
            "posed_baked_mesh_matches",
        ):
            self.assertNotIn(f'"{field}": true', report_source)
            self.assertIn(f'"{field}":', binding_source)
        for field in ("profile_root", "skeleton_3d", "mesh_instance_3d", "static_body_3d"):
            self.assertNotIn(f'"{field}": 1', report_source)
            self.assertIn(f'"{field}":', node_source)
        self.assertNotIn('"collision_shape_3d": profile.body.get_child_count()', report_source)
        self.assertNotIn('"total_profile_nodes": 4 + profile.body.get_child_count()', report_source)
        for expression in (
            "skeleton.get_bone_name",
            "skeleton.get_bone_parent",
            "skeleton.get_bone_rest",
            "skin.get_bind_bone",
            "skin.get_bind_pose",
            "mesh_instance.get_skeleton_path",
            "mesh_instance.get_skin",
            "mesh_instance.get_skin_reference",
            "skeleton.get_bone_pose",
            "body.get_child_count",
            "body_node.get_children",
        ):
            self.assertIn(expression, source)

    def test_report_validator_accepts_complete_binding_evidence(self) -> None:
        payload, report = _skeletal_validation_fixture()
        self.assertIn("coordinate_rule", report)
        self.assertNotIn("coordinate_mapping", report)
        smoke._validate_report(report, payload, DEFAULTS)

    def test_semantic_pose_runtime_quaternion_tolerance_is_bounded(self) -> None:
        rules = []
        readback = []
        for index in range(smoke.BONE_COUNT):
            role = f"test-role-{index}"
            rules.append(
                {
                    "kind": "joint",
                    "role": role,
                    "anchors": [],
                    "rotation_xyzw": [0.0, 0.0, 0.0, 1.0],
                }
            )
            readback.append(
                {
                    "selector": f"joint|{role}|",
                    "runtime_bone_id": f"test-bone-{index}",
                    "observed_rotation_xyzw": [0.0, 0.0, 0.0, 1.0],
                    "max_component_error_to_command": 0.0,
                }
            )
        command = {"rules": rules}
        target = {"instance_id": "test-avatar"}
        actual = {
            "target": deepcopy(target),
            "rule_readback": readback,
            "rules_observed": smoke.BONE_COUNT,
            "local_pose_matches_command": smoke.BONE_COUNT,
            "global_pose_matches_published": smoke.BONE_COUNT,
            "skin_matrices_match_published": smoke.BONE_COUNT,
            "applied": True,
        }
        accepted_error = smoke.SEMANTIC_POSE_QUATERNION_TOLERANCE * 0.9
        actual["rule_readback"][0]["observed_rotation_xyzw"] = [
            accepted_error,
            0.0,
            0.0,
            math.sqrt(1.0 - accepted_error * accepted_error),
        ]
        actual["rule_readback"][0]["max_component_error_to_command"] = accepted_error
        smoke._validate_command_injection(actual, target, command, "test-profile")

        rejected_error = smoke.SEMANTIC_POSE_QUATERNION_TOLERANCE + 1.0e-8
        actual["rule_readback"][0]["observed_rotation_xyzw"] = [
            rejected_error,
            0.0,
            0.0,
            math.sqrt(1.0 - rejected_error * rejected_error),
        ]
        actual["rule_readback"][0]["max_component_error_to_command"] = rejected_error
        with self.assertRaisesRegex(smoke.SmokeError, "does not match the command"):
            smoke._validate_command_injection(actual, target, command, "test-profile")

    def test_report_validator_rejects_numeric_boolean_substitutes(self) -> None:
        payload, report = _skeletal_validation_fixture()
        report["scope_flags"]["physics_stepping"] = 0
        with self.assertRaisesRegex(smoke.SmokeError, "scope flags are not fail-closed"):
            smoke._validate_report(report, payload, DEFAULTS)

        payload, report = _skeletal_validation_fixture()
        report["pose_binding"]["rules_validated"] = 1
        with self.assertRaisesRegex(smoke.SmokeError, "pose binding evidence is invalid"):
            smoke._validate_report(report, payload, DEFAULTS)

        payload, report = _skeletal_validation_fixture()
        report["profiles"][0]["binding"]["max_posed_vertex_error"] = 10**1000
        with self.assertRaisesRegex(smoke.SmokeError, "non-finite or unbounded numeric evidence"):
            smoke._validate_report(report, payload, DEFAULTS)

        payload, report = _skeletal_validation_fixture()
        report["profiles"][0]["neutral_mesh_aabb"] = deepcopy(report["profiles"][0]["neutral_mesh_aabb"])
        report["profiles"][0]["neutral_mesh_aabb"]["min"][0] = 10**1000
        with self.assertRaisesRegex(smoke.SmokeError, "non-finite or unbounded numeric evidence"):
            smoke._validate_report(report, payload, DEFAULTS)

    def test_report_validator_accepts_exact_carrier_identity(self) -> None:
        payload, report = _skeletal_validation_fixture()
        report["validated_carrier"] = deepcopy(CARRIER_IDENTITY)
        report["carrier_avatar_bindings"] = deepcopy(smoke._expected_carrier_avatar_bindings(CARRIER_AVATAR_RECORDS))
        smoke._validate_report(
            report,
            payload,
            DEFAULTS,
            deepcopy(CARRIER_IDENTITY),
            deepcopy(CARRIER_AVATAR_RECORDS),
        )

    def test_report_validator_rejects_aggregate_only_and_tampered_avatar_bindings(self) -> None:
        mutations = {
            "aggregate-only": None,
            "missing record": [],
            "duplicate instance": deepcopy(smoke._expected_carrier_avatar_bindings(CARRIER_AVATAR_RECORDS)),
            "reordered records": list(reversed(smoke._expected_carrier_avatar_bindings(CARRIER_AVATAR_RECORDS))),
            "swapped profiles": deepcopy(smoke._expected_carrier_avatar_bindings(CARRIER_AVATAR_RECORDS)),
            "mismatched candidate identity": deepcopy(smoke._expected_carrier_avatar_bindings(CARRIER_AVATAR_RECORDS)),
        }
        mutations["duplicate instance"][1]["instance_id"] = mutations["duplicate instance"][0]["instance_id"]
        mutations["swapped profiles"][0]["profile_id"], mutations["swapped profiles"][1]["profile_id"] = (
            mutations["swapped profiles"][1]["profile_id"],
            mutations["swapped profiles"][0]["profile_id"],
        )
        mutations["mismatched candidate identity"][0]["candidate_profile_sha256"] = "f" * 64
        for label, bindings in mutations.items():
            with self.subTest(case=label):
                payload, report = _skeletal_validation_fixture()
                report["validated_carrier"] = deepcopy(CARRIER_IDENTITY)
                if bindings is not None:
                    report["carrier_avatar_bindings"] = bindings
                with self.assertRaisesRegex(smoke.SmokeError, "carrier avatar binding|aggregate-only"):
                    smoke._validate_report(
                        report,
                        payload,
                        DEFAULTS,
                        deepcopy(CARRIER_IDENTITY),
                        deepcopy(CARRIER_AVATAR_RECORDS),
                    )

    def test_report_validator_rejects_inconsistent_carrier_expectations(self) -> None:
        payload, report = _skeletal_validation_fixture()
        report["validated_carrier"] = deepcopy(CARRIER_IDENTITY)
        report["carrier_avatar_bindings"] = deepcopy(smoke._expected_carrier_avatar_bindings(CARRIER_AVATAR_RECORDS))
        with self.assertRaisesRegex(smoke.SmokeError, "must be supplied together"):
            smoke._validate_report(report, payload, DEFAULTS, deepcopy(CARRIER_IDENTITY))

        mutations = {
            "instance IDs": (deepcopy(CARRIER_IDENTITY), deepcopy(CARRIER_AVATAR_RECORDS)),
            "profile order": (deepcopy(CARRIER_IDENTITY), deepcopy(CARRIER_AVATAR_RECORDS)),
            "candidate identity": (deepcopy(CARRIER_IDENTITY), deepcopy(CARRIER_AVATAR_RECORDS)),
        }
        mutations["instance IDs"][0]["experiment_instance_ids"][0] = "different-left"
        mutations["profile order"][1][0]["profile_id"], mutations["profile order"][1][1]["profile_id"] = (
            mutations["profile order"][1][1]["profile_id"],
            mutations["profile order"][1][0]["profile_id"],
        )
        mutations["candidate identity"][1][0]["candidate_profile_sha256"] = "f" * 64
        for label, (identity, records) in mutations.items():
            with self.subTest(case=label):
                with self.assertRaisesRegex(smoke.SmokeError, "expectations are inconsistent"):
                    smoke._validate_report(report, payload, DEFAULTS, identity, records)

    def test_no_carrier_report_rejects_unexpected_avatar_bindings(self) -> None:
        payload, report = _skeletal_validation_fixture()
        report["carrier_avatar_bindings"] = deepcopy(smoke._expected_carrier_avatar_bindings(CARRIER_AVATAR_RECORDS))
        with self.assertRaisesRegex(smoke.SmokeError, "no-carrier"):
            smoke._validate_report(report, payload, DEFAULTS)

    def test_carrier_loader_is_cached_and_identity_uses_carrier_canonicalizer(self) -> None:
        self.assertIs(smoke._load_carrier_module(), smoke._load_carrier_module())
        module = SimpleNamespace(
            SCHEMA=carrier.SCHEMA,
            BOUNDARY=carrier.BOUNDARY,
            _canonical_json=lambda _: b"carrier-owned-canonical-bytes\n",
        )
        value = {
            "instances": [
                {"instance_id": "avatar-left"},
                {"instance_id": "avatar-right"},
            ]
        }
        identity = smoke._carrier_identity(value, module)
        self.assertEqual(
            identity["sha256"],
            hashlib.sha256(b"carrier-owned-canonical-bytes\n").hexdigest(),
        )
        self.assertEqual(identity["byte_count_decimal"], "30")

    def test_report_validator_rejects_invalid_or_unexpected_carrier_identity(self) -> None:
        payload, report = _skeletal_validation_fixture()
        report["validated_carrier"] = None
        with self.assertRaisesRegex(smoke.SmokeError, "unexpected validated-carrier"):
            smoke._validate_report(report, payload, DEFAULTS)

        mutations = (
            ("sha256", "f" * 64),
            ("byte_count_decimal", 1234),
            ("byte_count_decimal", "01234"),
            ("byte_count_decimal", "1234.0"),
            ("schema", "unexpected"),
            ("boundary", "unexpected"),
            ("experiment_instance_ids", ["avatar-right", "avatar-left"]),
            ("experiment_instance_ids", ["avatar-left", "avatar-left"]),
            ("experiment_instance_ids", ["avatar-left", 1]),
        )
        for key, replacement in mutations:
            with self.subTest(key=key, replacement=replacement):
                payload, report = _skeletal_validation_fixture()
                report["validated_carrier"] = deepcopy(CARRIER_IDENTITY)
                report["validated_carrier"][key] = replacement
                with self.assertRaisesRegex(smoke.SmokeError, "validated-carrier identity is invalid"):
                    smoke._validate_report(
                        report,
                        payload,
                        DEFAULTS,
                        deepcopy(CARRIER_IDENTITY),
                        deepcopy(CARRIER_AVATAR_RECORDS),
                    )

        payload, report = _skeletal_validation_fixture()
        report["validated_carrier"] = {**deepcopy(CARRIER_IDENTITY), "extra": False}
        with self.assertRaisesRegex(smoke.SmokeError, "validated-carrier identity is incomplete"):
            smoke._validate_report(
                report,
                payload,
                DEFAULTS,
                deepcopy(CARRIER_IDENTITY),
                deepcopy(CARRIER_AVATAR_RECORDS),
            )

    def test_carrier_flow_passes_validated_payload_and_identity_through_unchanged(self) -> None:
        payload, report = _skeletal_validation_fixture()
        carrier_value = {
            "schema": carrier.SCHEMA,
            "boundary": carrier.BOUNDARY,
            "instances": [
                {
                    "instance_id": "avatar-left",
                    "profile_id": DEFAULTS[0],
                    "candidate_profile_sha256": "a" * 64,
                },
                {
                    "instance_id": "avatar-right",
                    "profile_id": DEFAULTS[1],
                    "candidate_profile_sha256": "b" * 64,
                },
            ],
        }
        module = SimpleNamespace(
            SCHEMA=carrier.SCHEMA,
            BOUNDARY=carrier.BOUNDARY,
            _canonical_json=carrier._canonical_json,
        )
        validated = (module, carrier_value, payload, DEFAULTS, ("avatar-left", "avatar-right"))
        expected_identity = smoke._carrier_identity(carrier_value, module)
        with (
            patch.object(smoke, "_validated_carrier_input", side_effect=[validated, validated]) as carrier_input,
            patch.object(smoke, "_launch_godot", return_value=("", "", 0, report)) as launch,
            patch.object(smoke, "_validate_report") as validate_report,
            patch.object(smoke.neutral_smoke, "_publish_report") as publish,
        ):
            result = smoke.run_skeletal_pose_smoke(
                self.root,
                None,
                self.root / "report.json",
                self.root / "carrier.json",
            )
        self.assertIs(result, report)
        self.assertEqual(carrier_input.call_count, 2)
        self.assertIs(launch.call_args.args[2], payload)
        self.assertEqual(launch.call_args.args[3], expected_identity)
        self.assertEqual(launch.call_args.args[4], CARRIER_AVATAR_RECORDS)
        validate_report.assert_called_once_with(
            report,
            payload,
            DEFAULTS,
            expected_identity,
            CARRIER_AVATAR_RECORDS,
        )
        publish.assert_called_once_with(self.root / "report.json", report)

    def test_carrier_profile_mismatch_and_postflight_change_fail_before_publication(self) -> None:
        payload, report = _skeletal_validation_fixture()
        carrier_value = {
            "schema": carrier.SCHEMA,
            "boundary": carrier.BOUNDARY,
            "instances": [
                {
                    "instance_id": "avatar-left",
                    "profile_id": DEFAULTS[0],
                    "candidate_profile_sha256": "a" * 64,
                },
                {
                    "instance_id": "avatar-right",
                    "profile_id": DEFAULTS[1],
                    "candidate_profile_sha256": "b" * 64,
                },
            ],
        }
        module = SimpleNamespace(
            SCHEMA=carrier.SCHEMA,
            BOUNDARY=carrier.BOUNDARY,
            _canonical_json=carrier._canonical_json,
        )
        validated = (module, carrier_value, payload, DEFAULTS, ("avatar-left", "avatar-right"))
        with (
            patch.object(smoke, "_validated_carrier_input", return_value=validated),
            patch.object(smoke, "_launch_godot") as launch,
        ):
            with self.assertRaisesRegex(smoke.SmokeError, "profile IDs disagree"):
                smoke.run_skeletal_pose_smoke(
                    self.root,
                    ALTERNATE,
                    self.root / "report.json",
                    self.root / "carrier.json",
                )
        launch.assert_not_called()

        changed_postflight = (module, carrier_value, payload, DEFAULTS, ("avatar-left", "avatar-changed"))
        with (
            patch.object(smoke, "_validated_carrier_input", side_effect=[validated, changed_postflight]),
            patch.object(smoke, "_launch_godot", return_value=("", "", 0, report)),
            patch.object(smoke, "_validate_report"),
            patch.object(smoke.neutral_smoke, "_publish_report") as publish,
        ):
            with self.assertRaisesRegex(smoke.SmokeError, "changed during"):
                smoke.run_skeletal_pose_smoke(
                    self.root,
                    None,
                    self.root / "report.json",
                    self.root / "carrier.json",
                )
        publish.assert_not_called()

    def test_semantic_pose_command_postflight_change_fails_before_publication(self) -> None:
        payload, report = _skeletal_validation_fixture()
        carrier_value = {
            "schema": carrier.SCHEMA,
            "boundary": carrier.BOUNDARY,
            "instances": deepcopy(CARRIER_AVATAR_RECORDS),
        }
        module = SimpleNamespace(
            SCHEMA=carrier.SCHEMA,
            BOUNDARY=carrier.BOUNDARY,
            _canonical_json=carrier._canonical_json,
        )
        validated = (module, carrier_value, payload, DEFAULTS, ("avatar-left", "avatar-right"))
        command_value = {"command": "initial"}
        changed_command = {"command": "mutated-after-launch"}
        command_identity = {"sha256": "a" * 64}
        semantic_payload = {"rules": [], "identity_frame": {}}
        command_results = [
            (semantic_command, command_value, command_identity, semantic_payload),
            (semantic_command, changed_command, command_identity, semantic_payload),
        ]
        with (
            patch.object(smoke, "_validated_carrier_input", side_effect=[validated, validated]),
            patch.object(smoke, "_validated_semantic_pose_command", side_effect=command_results),
            patch.object(smoke, "_launch_godot", return_value=("", "", 0, report)),
            patch.object(smoke, "_validate_report"),
            patch.object(smoke.neutral_smoke, "_publish_report") as publish,
        ):
            with self.assertRaisesRegex(smoke.SmokeError, "semantic pose command.*changed during"):
                smoke.run_skeletal_pose_smoke(
                    self.root,
                    None,
                    self.root / "report.json",
                    self.root / "carrier.json",
                    self.root / "command.json",
                )
        publish.assert_not_called()

    def test_semantic_contact_command_postflight_change_fails_before_publication(self) -> None:
        payload, report = _skeletal_validation_fixture()
        projection_value, projection_identity, carrier_value, records, profile_ids = _projection_fixture(payload)
        carrier_module = SimpleNamespace(
            SCHEMA=carrier.SCHEMA,
            BOUNDARY=carrier.BOUNDARY,
            _canonical_json=carrier._canonical_json,
        )
        validated = (carrier_module, carrier_value, payload, profile_ids, tuple(record["instance_id"] for record in records))
        command_value = {"command": "pose"}
        command_identity = {"sha256": "p" * 64}
        semantic_payload = {"rules": []}
        contact_value, contact_identity = _contact_command_fixture()
        changed_contact = deepcopy(contact_value)
        changed_contact["interaction"]["kind"] = "changed-contact"
        changed_contact_identity = {"sha256": "d" * 64}
        with (
            patch.object(smoke, "_validated_carrier_input", side_effect=[validated, validated]),
            patch.object(smoke, "_validated_projection_input", side_effect=[(None, projection_value, projection_identity), (None, projection_value, projection_identity)]),
            patch.object(
                smoke,
                "_validated_semantic_pose_command",
                side_effect=[
                    (semantic_command, command_value, command_identity, semantic_payload),
                    (semantic_command, command_value, command_identity, semantic_payload),
                ],
            ),
            patch.object(
                smoke,
                "_validated_semantic_contact_command",
                side_effect=[
                    (None, contact_value, contact_identity),
                    (None, changed_contact, changed_contact_identity),
                ],
            ),
            patch.object(smoke, "_launch_godot", return_value=("", "", 0, report)),
            patch.object(smoke, "_validate_report"),
            patch.object(smoke.neutral_smoke, "_publish_report") as publish,
        ):
            with self.assertRaisesRegex(smoke.SmokeError, "semantic contact command.*changed during"):
                smoke.run_skeletal_pose_smoke(
                    self.root,
                    None,
                    self.root / "report.json",
                    self.root / "carrier.json",
                    self.root / "pose.json",
                    self.root / "projection.json",
                    self.root / "creature-kernel",
                    self.root / "contact.json",
                )
        publish.assert_not_called()

    def test_report_validator_rejects_incomplete_or_over_tolerance_binding(self) -> None:
        payload, report = _skeletal_validation_fixture()
        report["profiles"][0]["binding"]["skin_bind_count"] = 17
        with self.assertRaisesRegex(smoke.SmokeError, "binding.skin_bind_count is invalid"):
            smoke._validate_report(report, payload, DEFAULTS)

        payload, report = _skeletal_validation_fixture()
        report["profiles"][0]["binding"]["max_posed_normal_error"] = smoke.NORMAL_TOLERANCE + 1.0e-7
        with self.assertRaisesRegex(smoke.SmokeError, "max_posed_normal_error exceeds tolerance"):
            smoke._validate_report(report, payload, DEFAULTS)

        payload, report = _skeletal_validation_fixture()
        report["profiles"][0]["binding"]["max_posed_vertex_error"] = -1.0
        with self.assertRaisesRegex(smoke.SmokeError, "max_posed_vertex_error must be non-negative"):
            smoke._validate_report(report, payload, DEFAULTS)

    def test_tampered_gallery_is_rejected_before_godot(self) -> None:
        if not GALLERY.is_dir():
            self.skipTest(f"cached completed gallery unavailable: {GALLERY}")
        tampered = self.root / "tampered-gallery"
        shutil.copytree(GALLERY, tampered)
        manifest_path = tampered / "structural-embodiment-gallery-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["profile_ids"] = list(reversed(manifest["profile_ids"]))
        manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
        with patch.object(smoke, "_launch_godot", side_effect=AssertionError("Godot was invoked after preflight rejection")):
            with self.assertRaises(smoke.SmokeError):
                smoke.run_skeletal_pose_smoke(tampered, DEFAULTS, self.root / "report.json")


@unittest.skipUnless(
    integration_available(),
    "attended X11 opt-in, exact Godot 4.7.2 renderer, X11 display, or configured gallery unavailable",
)
class SkeletalPoseSmokeIntegrationTests(unittest.TestCase):
    def test_real_carrier_load_through_records_exact_input_identity(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ck-godot-skeletal-pose-carrier-") as temporary:
            root = Path(temporary)
            carrier_path = root / "carrier.json"
            carrier.write_carrier(
                carrier_path,
                carrier.build_carrier(GALLERY, DEFAULTS, ("avatar-left", "avatar-right")),
            )
            report = smoke.run_skeletal_pose_smoke(
                GALLERY,
                None,
                root / "report.json",
                carrier_path,
            )
            carrier_bytes = carrier_path.read_bytes()
        self.assertEqual(report["profile_ids"], list(DEFAULTS))
        self.assertEqual(
            report["validated_carrier"],
            {
                "sha256": hashlib.sha256(carrier_bytes).hexdigest(),
                "byte_count_decimal": str(len(carrier_bytes)),
                "schema": carrier.SCHEMA,
                "boundary": carrier.BOUNDARY,
                "experiment_instance_ids": ["avatar-left", "avatar-right"],
            },
        )
        self.assertEqual(
            report["carrier_avatar_bindings"],
            smoke._expected_carrier_avatar_bindings(
                [
                    {
                        "instance_id": "avatar-left",
                        "profile_id": DEFAULTS[0],
                        "candidate_profile_sha256": report["profiles"][0]["candidate_profile_sha256"],
                    },
                    {
                        "instance_id": "avatar-right",
                        "profile_id": DEFAULTS[1],
                        "candidate_profile_sha256": report["profiles"][1]["candidate_profile_sha256"],
                    },
                ]
            ),
        )

    def test_real_semantic_pose_command_injects_to_both_carrier_bound_avatars(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ck-godot-semantic-pose-command-") as temporary:
            root = Path(temporary)
            carrier_path = root / "carrier.json"
            command_path = root / "command.json"
            carrier_value = carrier.build_carrier(GALLERY, DEFAULTS, ("avatar-left", "avatar-right"))
            carrier.write_carrier(carrier_path, carrier_value)
            command_value = semantic_command.build_command(GALLERY, carrier_path)
            semantic_command.write_command(command_path, command_value)
            report = smoke.run_skeletal_pose_smoke(
                GALLERY,
                None,
                root / "report.json",
                carrier_path,
                command_path,
            )
        self.assertEqual(report["semantic_pose_command_identity"], semantic_command.command_identity(command_value))
        self.assertEqual(report["semantic_pose_targets"], command_value["targets"])
        self.assertEqual(report["semantic_pose_frame"], command_value["identity_frame"])
        self.assertEqual(
            [profile["semantic_pose_injection"]["target"]["instance_id"] for profile in report["profiles"]],
            ["avatar-left", "avatar-right"],
        )
        for profile in report["profiles"]:
            injection = profile["semantic_pose_injection"]
            self.assertEqual(
                [record["selector"] for record in injection["rule_readback"]],
                [smoke._command_selector(rule) for rule in command_value["rules"]],
            )
            self.assertEqual(len({record["runtime_bone_id"] for record in injection["rule_readback"]}), smoke.BONE_COUNT)
            self.assertEqual(injection["rules_observed"], smoke.BONE_COUNT)
            self.assertEqual(injection["local_pose_matches_command"], smoke.BONE_COUNT)
            self.assertEqual(injection["global_pose_matches_published"], smoke.BONE_COUNT)
            self.assertEqual(injection["skin_matrices_match_published"], smoke.BONE_COUNT)
            self.assertTrue(injection["applied"])

    def test_real_projection_and_semantic_pose_command_share_exact_identity(self) -> None:
        if not REAL_CLI.is_file() or not os.access(REAL_CLI, os.X_OK):
            self.skipTest("debug Creature Kernel CLI unavailable for the real projection path")
        with tempfile.TemporaryDirectory(prefix="ck-godot-projection-semantic-pose-") as temporary:
            root = Path(temporary)
            carrier_path = root / "carrier.json"
            projection_path = root / "projection.json"
            command_path = root / "command.json"
            carrier_value = carrier.build_carrier(GALLERY, DEFAULTS, ("projection-left", "projection-right"))
            carrier.write_carrier(carrier_path, carrier_value)
            projection_value = projection.build_projection(
                GALLERY,
                carrier_path,
                cli_path=REAL_CLI,
            )
            projection.write_projection(projection_path, projection_value)
            command_value = semantic_command.build_command(GALLERY, carrier_path)
            semantic_command.write_command(command_path, command_value)
            report = smoke.run_skeletal_pose_smoke(
                GALLERY,
                None,
                root / "report.json",
                carrier_path,
                command_path,
                projection_path,
                REAL_CLI,
            )
        self.assertEqual(report["validated_ck_projection"], projection.projection_identity(projection_value))
        self.assertEqual(
            [profile["ck_projection_binding"] for profile in report["profiles"]],
            smoke._projection_bindings(projection_value),
        )
        self.assertTrue(all(profile["semantic_pose_injection"]["applied"] for profile in report["profiles"]))

    def test_real_semantic_contact_command_produces_bounded_runtime_response(self) -> None:
        if not smoke.CONTACT_COMMAND_MODULE_PATH.is_file():
            self.skipTest("disposable semantic contact command module unavailable")
        if not REAL_CLI.is_file() or not os.access(REAL_CLI, os.X_OK):
            self.skipTest("debug Creature Kernel CLI unavailable for the real contact path")
        contact = load_module(
            "disposable_semantic_contact_command_for_skeletal_tests",
            smoke.CONTACT_COMMAND_MODULE_PATH,
        )
        with tempfile.TemporaryDirectory(prefix="ck-godot-semantic-contact-") as temporary:
            root = Path(temporary)
            carrier_path = root / "carrier.json"
            pose_path = root / "pose.json"
            projection_path = root / "projection.json"
            contact_path = root / "contact.json"
            carrier.write_carrier(
                carrier_path,
                carrier.build_carrier(GALLERY, DEFAULTS, ("contact-actuator", "contact-response")),
            )
            pose_value = semantic_command.build_command(GALLERY, carrier_path)
            semantic_command.write_command(pose_path, pose_value)
            projection_value = projection.build_projection(GALLERY, carrier_path, cli_path=REAL_CLI)
            projection.write_projection(projection_path, projection_value)
            contact_value = contact.build_contact_command(GALLERY, carrier_path, pose_path)
            contact.write_contact_command(contact_path, contact_value)
            report = smoke.run_skeletal_pose_smoke(
                GALLERY,
                None,
                root / "report.json",
                carrier_path,
                pose_path,
                projection_path,
                REAL_CLI,
                contact_path,
            )
        self.assertEqual(report["scope_flags"], smoke.CONTACT_REPORT_FLAGS)
        self.assertEqual(report["boundary"], smoke.CONTACT_REPORT_BOUNDARY)
        self.assertEqual(report["coordinate_rule"]["scope"], smoke.CONTACT_REPORT_BOUNDARY)
        self.assertNotIn("coordinate_mapping", report)
        self.assertEqual(report["semantic_contact"]["phase_order"], smoke.CONTACT_PHASE_ORDER)
        self.assertNotIn("contact_events", report["semantic_contact"])
        self.assertEqual(
            set(report["semantic_contact"]["solver_impulses"][0]),
            {"runtime_derived", "target_indices", "shape_indices", "impulse_magnitude", "contact_samples"},
        )
        self.assertEqual(
            set(report["semantic_contact"]["response"]),
            {"target_index", "shape_index", "normal", "snapshots", "normal_velocity_delta", "normal_displacement", "displacement"},
        )
        self.assertEqual(
            set(report["semantic_contact"]["response"]["snapshots"]),
            {"initial", "contact", "final"},
        )

    def test_real_semantic_contact_deforms_and_recovers_smooth_forearm_surface(self) -> None:
        if not smoke.CONTACT_COMMAND_MODULE_PATH.is_file():
            self.skipTest("disposable semantic contact command module unavailable")
        if not REAL_CLI.is_file() or not os.access(REAL_CLI, os.X_OK):
            self.skipTest("debug Creature Kernel CLI unavailable for the real deformation path")
        contact = load_module(
            "disposable_semantic_contact_command_for_deformation_tests",
            smoke.CONTACT_COMMAND_MODULE_PATH,
        )
        with tempfile.TemporaryDirectory(prefix="ck-godot-semantic-deformation-") as temporary:
            root = Path(temporary)
            carrier_path = root / "carrier.json"
            pose_path = root / "pose.json"
            projection_path = root / "projection.json"
            contact_path = root / "contact.json"
            captures_path = root / "deformation-captures"
            carrier.write_carrier(
                carrier_path,
                carrier.build_carrier(GALLERY, DEFAULTS, ("deformation-actuator", "deformation-response")),
            )
            pose_value = semantic_command.build_command(GALLERY, carrier_path)
            semantic_command.write_command(pose_path, pose_value)
            projection_value = projection.build_projection(GALLERY, carrier_path, cli_path=REAL_CLI)
            projection.write_projection(projection_path, projection_value)
            contact_value = contact.build_contact_command(GALLERY, carrier_path, pose_path)
            contact.write_contact_command(contact_path, contact_value)

            report = smoke.run_skeletal_pose_smoke(
                GALLERY,
                None,
                root / "report.json",
                carrier_path,
                pose_path,
                projection_path,
                REAL_CLI,
                contact_path,
                captures_path,
            )

            self.assertEqual(report["scope_flags"], smoke.DEFORMATION_REPORT_FLAGS)
            self.assertEqual(report["boundary"], smoke.DEFORMATION_REPORT_BOUNDARY)
            deformation = report["semantic_deformation"]
            self.assertEqual(deformation["surface"]["kind"], smoke.DEFORMATION_SURFACE_KIND)
            self.assertAlmostEqual(
                deformation["drive"]["normalized_peak_depth"],
                smoke.DEFORMATION_NORMALIZED_PEAK_DEPTH,
                delta=smoke.TOLERANCE,
            )
            self.assertEqual(
                deformation["states"]["reference"]["vertices"],
                deformation["states"]["recovered"]["vertices"],
            )
            self.assertEqual(
                {path.name for path in captures_path.iterdir()},
                set(smoke.DEFORMATION_CAPTURE_NAMES),
            )
            for record in deformation["captures"]:
                capture = captures_path / record["file_name"]
                data = capture.read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), record["sha256"])
                self.assertEqual(str(len(data)), record["byte_count_decimal"])
                self.assertEqual(record["width"], smoke.DEFORMATION_CAPTURE_WIDTH)
                self.assertEqual(record["height"], smoke.DEFORMATION_CAPTURE_HEIGHT)

    def test_real_command_mode_does_not_read_shared_pose_file_after_injection(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ck-godot-semantic-pose-no-fallback-") as temporary:
            root = Path(temporary)
            gallery = root / "gallery"
            shutil.copytree(GALLERY, gallery)
            carrier_path = root / "carrier.json"
            carrier.write_carrier(
                carrier_path,
                carrier.build_carrier(gallery, DEFAULTS, ("no-fallback-left", "no-fallback-right")),
            )
            carrier_module, carrier_value, payload, profile_ids, _instance_ids = smoke._validated_carrier_input(
                gallery,
                carrier_path,
            )
            command_value = semantic_command.build_command(gallery, carrier_path)
            command_identity = semantic_command.command_identity(command_value)
            semantic_payload = semantic_command.semantic_payload(command_value)
            carrier_identity = smoke._carrier_identity(carrier_value, carrier_module)
            carrier_records = smoke._carrier_avatar_records(carrier_value)
            (gallery / semantic_command.POSE_FILE).unlink()
            stdout, stderr, returncode, report = smoke._launch_godot(
                gallery,
                profile_ids,
                payload,
                carrier_identity,
                carrier_records,
                command_value,
                command_identity,
                semantic_payload,
            )
        self.assertEqual(returncode, 0, f"stdout={stdout!r}; stderr={stderr!r}")
        self.assertIsNotNone(report)
        smoke._validate_report(
            report,
            payload,
            profile_ids,
            carrier_identity,
            carrier_records,
            command_value,
            command_identity,
        )

    def test_real_empty_semantic_arguments_fail_closed_without_file_fallback(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ck-godot-semantic-pose-empty-arguments-") as temporary:
            root = Path(temporary)
            carrier_path = root / "carrier.json"
            carrier.write_carrier(
                carrier_path,
                carrier.build_carrier(GALLERY, DEFAULTS, ("empty-left", "empty-right")),
            )
            carrier_module, carrier_value, payload, profile_ids, _instance_ids = smoke._validated_carrier_input(
                GALLERY,
                carrier_path,
            )
            carrier_identity = smoke._carrier_identity(carrier_value, carrier_module)
            carrier_records = smoke._carrier_avatar_records(carrier_value)
            empty_serializer = SimpleNamespace(_canonical_json=lambda _value: b"\n")
            with (
                patch.object(smoke, "_load_command_module", return_value=empty_serializer),
                self.assertRaisesRegex(smoke.SmokeError, "semantic pose command is not the canonical injected JSON text"),
            ):
                smoke._launch_godot(
                    GALLERY,
                    profile_ids,
                    payload,
                    carrier_identity,
                    carrier_records,
                    {},
                    {},
                    {},
                )

    def test_command_mode_rerun_is_deterministic_and_keeps_repository_clean(self) -> None:
        before_godot_dirs = {path for path in REPOSITORY_ROOT.rglob(".godot") if path.is_dir()}
        before_python_cache_dirs = {path for path in REPOSITORY_ROOT.rglob("__pycache__") if path.is_dir()}
        before_status = subprocess.run(
            ["git", "status", "--short", "--", str(EXPERIMENT)], capture_output=True, text=True, check=True
        ).stdout
        with tempfile.TemporaryDirectory(prefix="ck-godot-semantic-pose-command-repeat-") as temporary:
            root = Path(temporary)
            carrier_path = root / "carrier.json"
            command_path = root / "command.json"
            carrier.write_carrier(
                carrier_path,
                carrier.build_carrier(GALLERY, ALTERNATE, ("alternate-left", "alternate-right")),
            )
            semantic_command.write_command(command_path, semantic_command.build_command(GALLERY, carrier_path))
            first_path = root / "first.json"
            second_path = root / "second.json"
            first = smoke.run_skeletal_pose_smoke(GALLERY, None, first_path, carrier_path, command_path)
            second = smoke.run_skeletal_pose_smoke(GALLERY, None, second_path, carrier_path, command_path)
            self.assertEqual(first, second)
            self.assertEqual(first_path.read_bytes(), second_path.read_bytes())
        after_status = subprocess.run(
            ["git", "status", "--short", "--", str(EXPERIMENT)], capture_output=True, text=True, check=True
        ).stdout
        self.assertEqual(before_status, after_status)
        self.assertEqual(before_godot_dirs, {path for path in REPOSITORY_ROOT.rglob(".godot") if path.is_dir()})
        self.assertEqual(before_python_cache_dirs, {path for path in REPOSITORY_ROOT.rglob("__pycache__") if path.is_dir()})

    def test_real_alternate_carrier_pair_binds_in_carrier_order(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ck-godot-skeletal-pose-alternate-carrier-") as temporary:
            root = Path(temporary)
            carrier_path = root / "carrier.json"
            carrier.write_carrier(
                carrier_path,
                carrier.build_carrier(GALLERY, ALTERNATE, ("alternate-left", "alternate-right")),
            )
            report = smoke.run_skeletal_pose_smoke(
                GALLERY,
                None,
                root / "report.json",
                carrier_path,
            )
        self.assertEqual(report["profile_ids"], list(ALTERNATE))
        self.assertEqual(
            [binding["instance_id"] for binding in report["carrier_avatar_bindings"]],
            ["alternate-left", "alternate-right"],
        )
        self.assertEqual(
            [binding["profile_id"] for binding in report["carrier_avatar_bindings"]],
            list(ALTERNATE),
        )

    def test_real_godot_rejects_noncanonical_carrier_byte_count(self) -> None:
        _, payload = smoke.neutral_smoke.preflight(GALLERY, DEFAULTS)
        invalid_identity = deepcopy(CARRIER_IDENTITY)
        invalid_identity["byte_count_decimal"] = 1234
        with self.assertRaisesRegex(smoke.SmokeError, "validated carrier byte count is invalid"):
            smoke._launch_godot(
                GALLERY,
                DEFAULTS,
                payload,
                invalid_identity,
                CARRIER_AVATAR_RECORDS,
            )

    def test_real_default_pair_produces_skeleton_skin_pose_and_proxy_evidence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ck-godot-skeletal-pose-default-") as temporary:
            report = smoke.run_skeletal_pose_smoke(GALLERY, DEFAULTS, Path(temporary) / "report.json")
        self.assertEqual(report["profile_ids"], list(DEFAULTS))
        for profile in report["profiles"]:
            self.assertEqual(profile["binding"]["skeleton_bone_count"], smoke.BONE_COUNT)
            self.assertEqual(profile["binding"]["skin_bind_count"], smoke.BONE_COUNT)
            self.assertEqual(profile["binding"]["pose_rules_applied"], smoke.BONE_COUNT)
            self.assertTrue(profile["binding"]["mesh_skin_bound"])
            self.assertEqual(profile["node_counts"]["collision_shape_3d"], smoke.PROXY_COUNT)

    def test_real_alternate_pair_is_reported_in_requested_order(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ck-godot-skeletal-pose-alternate-") as temporary:
            report = smoke.run_skeletal_pose_smoke(GALLERY, ALTERNATE, Path(temporary) / "report.json")
        self.assertEqual(report["profile_ids"], list(ALTERNATE))
        self.assertEqual([profile["profile_id"] for profile in report["profiles"]], list(ALTERNATE))

    def test_real_malformed_skeleton_and_pose_are_rejected_fail_closed(self) -> None:
        for mutation, expected_error in (("skeleton", "skeleton states must contain exactly 18 bones"), ("pose", "shared pose rule 0 does not match")):
            with self.subTest(mutation=mutation):
                with tempfile.TemporaryDirectory(prefix=f"ck-godot-skeletal-pose-{mutation}-") as temporary:
                    gallery = Path(temporary) / "gallery"
                    shutil.copytree(GALLERY, gallery)
                    _, payload = smoke.neutral_smoke.preflight(gallery, DEFAULTS)
                    if mutation == "skeleton":
                        _mutate_skeleton(gallery, payload, DEFAULTS[0])
                    else:
                        _mutate_pose(gallery, payload)
                    with self.assertRaisesRegex(smoke.SmokeError, expected_error):
                        smoke._launch_godot(gallery, DEFAULTS, payload)

    def test_real_rerun_is_deterministic_and_does_not_pollute_repository_or_cache(self) -> None:
        before_godot_dirs = {path for path in REPOSITORY_ROOT.rglob(".godot") if path.is_dir()}
        before_python_cache_dirs = {path for path in REPOSITORY_ROOT.rglob("__pycache__") if path.is_dir()}
        before_status = subprocess.run(
            ["git", "status", "--short", "--", str(EXPERIMENT)], capture_output=True, text=True, check=True
        ).stdout
        with tempfile.TemporaryDirectory(prefix="ck-godot-skeletal-pose-deterministic-") as temporary:
            root = Path(temporary)
            first_path = root / "first.json"
            second_path = root / "second.json"
            first = smoke.run_skeletal_pose_smoke(GALLERY, DEFAULTS, first_path)
            second = smoke.run_skeletal_pose_smoke(GALLERY, DEFAULTS, second_path)
            self.assertEqual(first, second)
            self.assertEqual(first_path.read_bytes(), second_path.read_bytes())
        after_godot_dirs = {path for path in REPOSITORY_ROOT.rglob(".godot") if path.is_dir()}
        after_python_cache_dirs = {path for path in REPOSITORY_ROOT.rglob("__pycache__") if path.is_dir()}
        after_status = subprocess.run(
            ["git", "status", "--short", "--", str(EXPERIMENT)], capture_output=True, text=True, check=True
        ).stdout
        self.assertEqual(before_godot_dirs, after_godot_dirs)
        self.assertEqual(before_python_cache_dirs, after_python_cache_dirs)
        self.assertEqual(before_status, after_status)

    def test_real_carrier_rerun_is_deterministic_and_does_not_pollute_repository_or_cache(self) -> None:
        before_godot_dirs = {path for path in REPOSITORY_ROOT.rglob(".godot") if path.is_dir()}
        before_python_cache_dirs = {path for path in REPOSITORY_ROOT.rglob("__pycache__") if path.is_dir()}
        before_status = subprocess.run(
            ["git", "status", "--short", "--", str(EXPERIMENT)], capture_output=True, text=True, check=True
        ).stdout
        with tempfile.TemporaryDirectory(prefix="ck-godot-skeletal-pose-carrier-deterministic-") as temporary:
            root = Path(temporary)
            carrier_path = root / "carrier.json"
            carrier.write_carrier(
                carrier_path,
                carrier.build_carrier(GALLERY, DEFAULTS, ("repeat-left", "repeat-right")),
            )
            first_path = root / "first.json"
            second_path = root / "second.json"
            first = smoke.run_skeletal_pose_smoke(GALLERY, None, first_path, carrier_path)
            second = smoke.run_skeletal_pose_smoke(GALLERY, None, second_path, carrier_path)
            self.assertEqual(first, second)
            self.assertEqual(first_path.read_bytes(), second_path.read_bytes())
        after_godot_dirs = {path for path in REPOSITORY_ROOT.rglob(".godot") if path.is_dir()}
        after_python_cache_dirs = {path for path in REPOSITORY_ROOT.rglob("__pycache__") if path.is_dir()}
        after_status = subprocess.run(
            ["git", "status", "--short", "--", str(EXPERIMENT)], capture_output=True, text=True, check=True
        ).stdout
        self.assertEqual(before_godot_dirs, after_godot_dirs)
        self.assertEqual(before_python_cache_dirs, after_python_cache_dirs)
        self.assertEqual(before_status, after_status)


if __name__ == "__main__":
    unittest.main()

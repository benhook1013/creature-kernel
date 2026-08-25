#!/usr/bin/env python3
"""Publish a disposable baseline-versus-successor surface comparison.

This is deliberately an adapter, not a surface renderer. It runs the current
filled-form producer once, then the baseline and successor experiment
generators in isolated temporary storage. Both bundles are validated against
the same source and capture frame before four baseline/successor image pairs
are published into the existing immutable image-review format. The result is
bounded technical and visual inspection evidence; it is not production
geometry or acceptance evidence. A published gallery may serve as a named
human checkpoint when the active runway explicitly identifies it as one.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import lzma
import math
import os
import selectors
import secrets
import shutil
import signal
import stat
import struct
import subprocess
import sys
import tempfile
import time
import zlib
from pathlib import Path
from typing import Any

import common
from common import ValidationError, canonical_json, validate_id
from publish import PublishError, _open_directory, publish_session
from publish_provisional_form import (
    ORDINARY_SOURCE_BYTES,
    ProvisionalFormPublishError,
    _copy_input_reference,
    _parse_inspection,
    _validate_input,
)


class SurfacePreviewPublishError(RuntimeError):
    """A bounded, user-facing publication failure."""


SURFACE_PREVIEW_FORMAT = "creature-kernel.disposable-surface-preview.v3"
REGIONAL_GUIDE_FORMAT = "creature-kernel.disposable-surface-preview-regional-guide.v11"
SUCCESSOR_PREVIEW_FORMAT = "creature-kernel.disposable-successor-surface-preview.v9"
SEMANTIC_SIDECAR_FORMAT = "creature-kernel.disposable-surface-preview-semantic-winners.v1"
SUCCESSOR_MANIFEST_NAME = "successor-surface-manifest.json"
SUCCESSOR_CONSUMER_ID = "successor-surface-v1"
SUCCESSOR_REGION_ID = "successor-torso-shoulder-head-neck-arm-leg-foot-profile-limb-extremity-tail-profile-sweeps-v12"
AUTHORED_TORSO_PROFILE_FORMAT = "creature-kernel.provisional-form-torso-profile.v1"
AUTHORED_TORSO_PROFILE_FRAME_ROLE = "form_torso_profile_control"
AUTHORED_TORSO_PROFILE_SECTION_NAMES = (
    "lower-pelvis",
    "upper-pelvis",
    "lower-abdomen",
    "waist-abdomen",
    "upper-abdomen",
    "lower-ribcage",
    "upper-ribcage-shoulder",
)
AUTHORED_TORSO_PROFILE_OWNER_ROLES = (
    "pelvis", "pelvis", "torso", "torso", "torso", "torso", "torso",
)
AUTHORED_TORSO_PROFILE_RADIUS_AXES = ("lateral", "anterior", "posterior")
AUTHORED_TORSO_PROFILE_DIMENSION_SUFFIXES = (
    "lateral_radius", "anterior_radius", "posterior_radius",
)
AUTHORED_TORSO_PROFILE_PROVENANCE_SOURCE = "source-authored"
AUTHORED_HEAD_NECK_PROFILE_FORMAT = common.PROVISIONAL_FORM_HEAD_NECK_PROFILE_FORMAT
AUTHORED_HEAD_NECK_PROFILE_FRAME_ROLE = common.PROVISIONAL_FORM_HEAD_NECK_PROFILE_FRAME_ROLE
AUTHORED_HEAD_NECK_PROFILE_SECTION_NAMES = common.PROVISIONAL_FORM_HEAD_NECK_PROFILE_SECTION_NAMES
AUTHORED_HEAD_NECK_PROFILE_OWNER_ROLES = common.PROVISIONAL_FORM_HEAD_NECK_PROFILE_OWNER_ROLES
AUTHORED_HEAD_NECK_PROFILE_RADIUS_AXES = tuple(
    axis for axis, _role_suffix in common.PROVISIONAL_FORM_HEAD_NECK_PROFILE_RADIUS_AXES
)
AUTHORED_HEAD_NECK_PROFILE_DIMENSION_SUFFIXES = tuple(
    suffix for _axis, suffix in common.PROVISIONAL_FORM_HEAD_NECK_PROFILE_RADIUS_AXES
)
AUTHORED_HEAD_NECK_PROFILE_FRAME_INDICES = {"head": 0, "neck": 1}
AUTHORED_HEAD_NECK_PROFILE_LANDMARK_INDICES = (6, 7, 2, 1, 0, 4, 3, 5)
AUTHORED_ARM_PROFILE_FORMAT = common.PROVISIONAL_FORM_ARM_PROFILE_FORMAT
AUTHORED_ARM_PROFILE_FRAME_ROLE = common.PROVISIONAL_FORM_ARM_PROFILE_FRAME_ROLE
AUTHORED_ARM_PROFILE_SIDE_NAMES = common.PROVISIONAL_FORM_ARM_PROFILE_SIDE_NAMES
AUTHORED_ARM_PROFILE_SECTION_NAMES = common.PROVISIONAL_FORM_ARM_PROFILE_SECTION_NAMES
AUTHORED_ARM_PROFILE_OWNER_ROLES = common.PROVISIONAL_FORM_ARM_PROFILE_OWNER_ROLES
AUTHORED_ARM_PROFILE_RADIUS_AXES = tuple(
    axis for axis, _role_suffix in common.PROVISIONAL_FORM_ARM_PROFILE_RADIUS_AXES
)
AUTHORED_ARM_PROFILE_DIMENSION_SUFFIXES = tuple(
    suffix for _axis, suffix in common.PROVISIONAL_FORM_ARM_PROFILE_RADIUS_AXES
)
AUTHORED_LEG_PROFILE_FORMAT = common.PROVISIONAL_FORM_LEG_PROFILE_FORMAT
AUTHORED_LEG_PROFILE_SIDE_NAMES = common.PROVISIONAL_FORM_LEG_PROFILE_SIDE_NAMES
AUTHORED_LEG_PROFILE_SECTION_NAMES = common.PROVISIONAL_FORM_LEG_PROFILE_SECTION_NAMES
AUTHORED_LEG_PROFILE_OWNER_ROLES = common.PROVISIONAL_FORM_LEG_PROFILE_OWNER_ROLES
AUTHORED_LEG_PROFILE_RADIUS_AXES = tuple(
    axis for axis, _role_suffix in common.PROVISIONAL_FORM_LEG_PROFILE_RADIUS_AXES
)
AUTHORED_LEG_PROFILE_DIMENSION_SUFFIXES = tuple(
    suffix for _axis, suffix in common.PROVISIONAL_FORM_LEG_PROFILE_RADIUS_AXES
)
AUTHORED_LEG_PROFILE_FRAME_ROLE = common.PROVISIONAL_FORM_LEG_PROFILE_FRAME_ROLE
AUTHORED_FOOT_PROFILE_FORMAT = common.PROVISIONAL_FORM_FOOT_PROFILE_FORMAT
AUTHORED_FOOT_PROFILE_FRAME_ROLE = common.PROVISIONAL_FORM_FOOT_PROFILE_FRAME_ROLE
AUTHORED_FOOT_PROFILE_SIDE_NAMES = common.PROVISIONAL_FORM_FOOT_PROFILE_SIDE_NAMES
AUTHORED_FOOT_PROFILE_SECTION_NAMES = common.PROVISIONAL_FORM_FOOT_PROFILE_SECTION_NAMES
AUTHORED_FOOT_PROFILE_OWNER_ROLES = common.PROVISIONAL_FORM_FOOT_PROFILE_OWNER_ROLES
AUTHORED_FOOT_PROFILE_RADIUS_AXES = tuple(
    axis for axis, _role_suffix in common.PROVISIONAL_FORM_FOOT_PROFILE_RADIUS_AXES
)
AUTHORED_FOOT_PROFILE_DIMENSION_SUFFIXES = tuple(
    suffix for _axis, suffix in common.PROVISIONAL_FORM_FOOT_PROFILE_RADIUS_AXES
)
AUTHORED_FOOT_PROFILE_HOCK_SECTION_INDEX = common.PROVISIONAL_FORM_FOOT_PROFILE_HOCK_SECTION_INDEX
SUCCESSOR_HEAD_NECK_ROUTE_TOPOLOGY = (
    ("vertical-neck-cranium", (0, 1, 2, 3, 4), "up", ("lateral", "forward"), (0, 1, 2, 3)),
    ("forward-muzzle", (3, 5, 6, 7), "forward", ("lateral", "up"), (4, 5, 6)),
)
EXPECTED_VARIANTS = common.PROVISIONAL_FORM_VARIANT_IDS
EXPECTED_VIEWS = ("front", "side", "three-quarter")
MANIFEST_NAME = "surface-preview-manifest.json"
EXPECTED_GENERATOR_OWNERSHIP = (
    "recipe fields are source-owned; the blended torso-cage is torso-owned; "
    "shoulder support curves remain torso-owned guide-only controls and are "
    "not consumed by this adapter; deltoid recipes retain their upper-arm "
    "owners; winner labels expose only source AddressKeys"
)
MAX_STDOUT_BYTES = common.MAX_STRUCTURE_JSON_BYTES
MAX_STDERR_BYTES = 64 * 1024
# The v9 successor manifest carries complete per-variant guide-derived leg/foot
# metadata plus the compact exact component inventory. Keep the existing bound
# explicit: current real publication fits it, but there is deliberately little
# room for duplicated diagnostic metadata.
MAX_MANIFEST_BYTES = 384 * 1024
MAX_GUIDE_BYTES = 512 * 1024
MAX_METRICS_BYTES = 256 * 1024
MAX_COMPONENT_BOUND_ABS = 100.0
MAX_ARTIFACT_BYTES = 16 * 1024 * 1024
# Winner labels scale with the validated mesh vertex count, unlike compact
# metrics and guide metadata.  Keep the byte cap finite while letting the
# dedicated semantic validator enforce the tighter structural bounds below.
MAX_SEMANTIC_SIDECAR_BYTES = MAX_ARTIFACT_BYTES
# The current producer uses the highest XZ preset, whose decoder needs a little
# over 64 MiB.  Keep a finite margin while rejecting untrusted dictionary
# declarations before liblzma can allocate against them.
MAX_LZMA_MEMORY_BYTES = 128 * 1024 * 1024
# The current fixed <=96-sample fixtures are far below these limits.  Keep
# them substantially tighter than the voxel-grid cardinality so an adversarial
# compact text artifact cannot turn the 16 MiB byte cap into excessive Python
# object/edge-map allocation.
MAX_SUCCESSOR_PLY_VERTICES = 100_000
MAX_SUCCESSOR_PLY_FACES = 200_000
# The current bounded successor meshes have unit-scale-ish coordinates and
# volumes many orders above this floor.  Scale the floor by a characteristic
# coordinate cubed so translated or uniformly scaled meshes use the same
# relative acceptance rule.
SUCCESSOR_PLY_VOLUME_RELATIVE_TOLERANCE = 1.0e-12
SUCCESSOR_PLY_VOLUME_ULP_MULTIPLIER = 64.0
SUCCESSOR_PLY_MIN_NORMAL_LENGTH = 1.0e-14
AUTHORED_TORSO_PROFILE_MIN_RADIUS_PERMILLE = 1
AUTHORED_TORSO_PROFILE_MAX_RADIUS_PERMILLE = 5_000
SOURCE_EVIDENCE_ENCODING = "utf-8"
SOURCE_EVIDENCE_TRANSFER = "base64"
SOURCE_EVIDENCE_COMPRESSION = "xz"
INPUT_EVIDENCE_PREFIX = "input_body_document"
PRODUCER_EVIDENCE_PREFIX = "producer_envelope"
INPUT_EVIDENCE_FIELDS = {
    "input_body_document_encoding",
    "input_body_document_bytes",
    "input_body_document_sha256",
}
MAX_BUNDLE_SCAN_DEPTH = 8
MAX_BUNDLE_SCAN_ENTRIES = 1024
MAX_BUNDLE_SCAN_BYTES = 128 * 1024 * 1024
MAX_BUNDLE_SCAN_SECONDS = 5.0
MAX_PNG_WIDTH = 4096
MAX_PNG_HEIGHT = 4096
MAX_PNG_DECODED_BYTES = MAX_PNG_WIDTH * MAX_PNG_HEIGHT * 4 + MAX_PNG_HEIGHT
READ_CHUNK = 64 * 1024
INSPECTION_TIMEOUT_SECONDS = 10.0
GENERATOR_TIMEOUT_SECONDS = 120.0
PROCESS_GRACE_SECONDS = 0.5
EXPECTED_CANVAS = {"width": 1800, "height": 1500, "mode": "RGB"}
EXPECTED_PROJECTIONS = [
    {"name": "front", "basis": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]], "base": "x-right/y-up/z-depth"},
    {"name": "side", "basis": [[0.0, 0.0, -1.0], [0.0, 1.0, 0.0], [1.0, 0.0, 0.0]], "base": "-z-right/y-up/x-depth"},
    {"name": "three-quarter", "basis": [[0.7071067811865475, 0.0, -0.7071067811865475], [0.0, 1.0, 0.0], [0.7071067811865475, 0.0, 0.7071067811865475]], "base": "front-right/y-up/depth"},
]
EXPECTED_LAYOUT = {
    "panel_order": [
        "front-control-guide",
        "side-control-guide",
        "three-quarter-control-guide",
        "front-field-components",
        "side-field-components",
        "three-quarter-field-components",
        "front-skin",
        "side-skin",
        "three-quarter-skin",
    ],
    "panels": [
        {"id": "front-control-guide", "projection": "front", "content": "control-guide", "box": [12, 72, 592, 532]},
        {"id": "side-control-guide", "projection": "side", "content": "control-guide", "box": [610, 72, 1190, 532]},
        {"id": "three-quarter-control-guide", "projection": "three-quarter", "content": "control-guide", "box": [1208, 72, 1788, 532]},
        {"id": "front-field-components", "projection": "front", "content": "field-components", "box": [12, 546, 592, 1006]},
        {"id": "side-field-components", "projection": "side", "content": "field-components", "box": [610, 546, 1190, 1006]},
        {"id": "three-quarter-field-components", "projection": "three-quarter", "content": "field-components", "box": [1208, 546, 1788, 1006]},
        {"id": "front-skin", "projection": "front", "content": "skin", "box": [12, 1020, 592, 1480]},
        {"id": "side-skin", "projection": "side", "content": "skin", "box": [610, 1020, 1190, 1480]},
        {"id": "three-quarter-skin", "projection": "three-quarter", "content": "skin", "box": [1208, 1020, 1788, 1480]},
    ],
    "pairing": "control-guide/field-components/skin per projection",
    "frame": "shared-world-bounds-and-projection-basis",
}
EXPECTED_COMPONENT_VISUALIZATION = {
    "mode": "exact-consumed-component-zero-isosurfaces",
    "samples_per_axis": 32,
    "stage": "pre-smooth-union",
    "colour_identity": "sha256-source-owner-and-recipe",
}
EXPECTED_COMPONENT_VISUALIZATION_METRICS = {
    "semantics": "pre-union exact zero-isosurfaces of every consumer-supplied component consumed by the smooth union; final skin remains neutral",
    "evaluator": "consumer-supplied exact callable",
    "evaluator_inventory_binding": "the exact _RenderComponent records passed to _render",
    "resolution": {"samples_per_axis": 32, "voxels_per_field": 32 ** 3},
    "bounds": {
        "source": "consumer-supplied per-component sampling bounds",
        "padding": 0.05,
        "clipping": "all six sample-domain faces must remain outside-positive",
    },
    "colour_identity": {
        "algorithm": "sha256(canonical source owner plus recipe)",
        "alpha": 112,
    },
}
EXPECTED_SUCCESSOR_COMPONENT_RECIPE_COUNTS = {
    "successor-torso-loft": 1,
    "successor-vertical-neck-cranium": 1,
    "successor-forward-muzzle": 1,
    "successor-left-upper-arm-route": 1,
    "successor-left-forearm-route": 1,
    "successor-right-upper-arm-route": 1,
    "successor-right-forearm-route": 1,
    "successor-left-leg": 1,
    "successor-right-leg": 1,
    "successor-left-hand-attachment": 1,
    "successor-left-hand-paw": 1,
    "successor-left-foot": 1,
    "successor-right-hand-attachment": 1,
    "successor-right-hand-paw": 1,
    "successor-right-foot": 1,
    "successor-tail-root-source": 1,
    "successor-tail-root-attachment": 1,
    "successor-tail-root-collar": 1,
    "successor-tail-tip-source": 1,
    "successor-tail-tip-extension": 1,
    "successor-tail-tip-cap": 1,
    "successor-left-shoulder-envelope": 1,
    "successor-right-shoulder-envelope": 1,
    "root-bridge": 2,
    "hip-transition": 2,
}
EXPECTED_GUIDE_COUNTS = {
    "owners": 18,
    "axial_stations": 3,
    "axial_transitions": 2,
    "axial_core_masses": 1,
    "torso_cage_sections": 7,
    "torso_cage_connections": 6,
    "shoulder_frame_sides": 2,
    "shoulder_frame_curves": 6,
    "shoulder_frame_compiled_fields": 2,
    "arm_profile_sides": 2,
    "arm_profile_sections": 10,
    "leg_profile_sides": 2,
    "leg_profile_sections": 10,
    "foot_profile_sides": 2,
    "foot_profile_sections": 4,
    "head": 1,
    "head_neck_profile_sections": 8,
    "head_neck_profile_connections": 7,
    "limbs": 8,
    "paws": 4,
    "tails": 2,
    "compiled_fields": 52,
    "compiled_field_recipe_counts": {
        "upper_arm-pre-joint": 2,
        "upper_arm-joint": 2,
        "forearm-proximal": 2,
        "forearm-distal": 2,
        "thigh-pre-joint": 2,
        "thigh-joint": 2,
        "shin-pre-joint": 2,
        "shin-joint": 2,
        "elbow": 2,
        "knee": 2,
        "hock": 2,
        "paw": 2,
        "metatarsal": 2,
        "paw-pad": 2,
        "toe-box": 2,
        "extremity-bridge": 2,
        "root-bridge": 4,
        "hip-transition": 2,
        "deltoid-sweep-1": 2,
        "tail-segment": 2,
        "cranium": 1,
        "muzzle": 1,
        "head-base-bridge": 1,
        "tapered-neck": 1,
        "neck-collar": 1,
        "torso-cage": 1,
        "tail-root-bridge": 1,
        "tail-root-collar": 1,
        "tail-tip-extension": 1,
        "tail-tip-cap": 1,
    },
}

EXPECTED_FIELD_RECIPES = (
    "torso-cage", "cranium", "muzzle", "head-base-bridge", "tapered-neck", "neck-collar",
    "upper_arm-pre-joint", "upper_arm-joint", "forearm-proximal", "forearm-distal",
    "thigh-pre-joint", "thigh-joint", "shin-pre-joint", "shin-joint", "elbow", "knee", "hock",
    "root-bridge", "hip-transition",
    "deltoid-sweep-1",
    "paw", "metatarsal", "paw-pad", "toe-box", "extremity-bridge",
    "tail-segment", "tail-tip-extension", "tail-tip-cap", "tail-root-bridge", "tail-root-collar",
)


def default_creature_kernel() -> Path:
    return Path(__file__).resolve().parents[2] / "target" / "debug" / "creature-kernel"


def default_generator() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "experiments"
        / "current-form-surface-preview"
        / "generate_surface_preview.py"
    )


def default_successor_generator() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "experiments"
        / "current-form-surface-preview"
        / "generate_successor_surface_preview.py"
    )


def _stop_process(process: subprocess.Popen[bytes], *, process_group_id: int | None = None) -> None:
    if os.name == "posix" and process_group_id is not None:
        try:
            os.killpg(process_group_id, signal.SIGTERM)
        except OSError:
            pass
    try:
        process.terminate()
    except OSError:
        pass
    try:
        process.wait(timeout=PROCESS_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        pass
    if os.name == "posix" and process_group_id is not None:
        try:
            os.killpg(process_group_id, signal.SIGKILL)
        except OSError:
            pass
    try:
        process.kill()
    except OSError:
        pass
    try:
        process.wait(timeout=PROCESS_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        pass


def _run_bounded(command: list[str], *, timeout: float, label: str) -> tuple[bytes, bytes, int]:
    """Run a fixed argv without a shell, with bounded output and process cleanup."""

    try:
        process = subprocess.Popen(
            command,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            close_fds=True,
            start_new_session=(os.name == "posix"),
        )
    except (OSError, ValueError) as exc:
        raise SurfacePreviewPublishError(f"cannot execute {label}: {exc}") from exc
    assert process.stdout is not None and process.stderr is not None
    process_group_id: int | None = None
    if os.name == "posix":
        try:
            candidate = os.getpgid(process.pid)
        except OSError:
            # start_new_session makes the child PID the session/process-group
            # ID.  Retain that ID if the direct child exits before inspection.
            candidate = process.pid
        # Never signal the caller's process group, even if process setup is
        # changed in the future or the child exits during setup.
        if candidate > 1 and candidate not in {os.getpid(), os.getpgrp()}:
            process_group_id = candidate
    selector = selectors.DefaultSelector()
    stdout_fd = process.stdout.fileno()
    stderr_fd = process.stderr.fileno()
    streams = {
        stdout_fd: (process.stdout, bytearray(), MAX_STDOUT_BYTES, "stdout"),
        stderr_fd: (process.stderr, bytearray(), MAX_STDERR_BYTES, "stderr"),
    }
    for stream, _, _, _ in streams.values():
        selector.register(stream, selectors.EVENT_READ)
    failure: SurfacePreviewPublishError | None = None
    try:
        deadline = time.monotonic() + timeout
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                failure = SurfacePreviewPublishError(f"{label} timed out after {timeout:g}s")
                _stop_process(process, process_group_id=process_group_id)
                break
            events = selector.select(remaining)
            if not events:
                failure = SurfacePreviewPublishError(f"{label} timed out after {timeout:g}s")
                _stop_process(process, process_group_id=process_group_id)
                break
            for key, _ in events:
                stream = key.fileobj
                fd = stream.fileno()
                _, buffer, limit, stream_name = streams[fd]
                chunk = os.read(fd, min(READ_CHUNK, limit - len(buffer) + 1))
                if not chunk:
                    selector.unregister(stream)
                    stream.close()
                    continue
                if len(chunk) > limit - len(buffer):
                    failure = SurfacePreviewPublishError(
                        f"{label} {stream_name} exceeded {limit} bytes"
                    )
                    _stop_process(process, process_group_id=process_group_id)
                    break
                buffer.extend(chunk)
            if failure is not None:
                break
        if failure is not None:
            raise failure
        try:
            returncode = process.wait(timeout=PROCESS_GRACE_SECONDS)
        except subprocess.TimeoutExpired as exc:
            _stop_process(process, process_group_id=process_group_id)
            raise SurfacePreviewPublishError(f"{label} did not exit") from exc
        # Preserve the direct child's completed status, then terminate any
        # surviving process in its private session before returning the
        # captured output.  This prevents a generator grandchild from
        # mutating a validated bundle during publication.
        _stop_process(process, process_group_id=process_group_id)
        return bytes(streams[stdout_fd][1]), bytes(streams[stderr_fd][1]), returncode
    finally:
        selector.close()
        for stream, _, _, _ in streams.values():
            try:
                stream.close()
            except OSError:
                pass
        if process.poll() is None:
            _stop_process(process, process_group_id=process_group_id)


def _read_json(path: Path, limit: int, where: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise SurfacePreviewPublishError(f"{where} must be a regular non-symlink file")
    try:
        if path.stat().st_size > limit:
            raise SurfacePreviewPublishError(f"{where} exceeds {limit} bytes")
        value = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
        )
    except SurfacePreviewPublishError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise SurfacePreviewPublishError(f"{where} is invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise SurfacePreviewPublishError(f"{where} must be a JSON object")
    return value


def _safe_relative(raw: Any, where: str) -> Path:
    if not isinstance(raw, str) or not raw or "\\" in raw or "\x00" in raw:
        raise SurfacePreviewPublishError(f"{where} must be a safe relative path")
    path = Path(raw)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise SurfacePreviewPublishError(f"{where} must be a safe relative path")
    return path


def _sha256(path: Path, where: str) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("rb") as stream:
            while True:
                chunk = stream.read(READ_CHUNK)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_ARTIFACT_BYTES:
                    raise SurfacePreviewPublishError(f"{where} exceeds {MAX_ARTIFACT_BYTES} bytes")
                digest.update(chunk)
    except SurfacePreviewPublishError:
        raise
    except OSError as exc:
        raise SurfacePreviewPublishError(f"could not read {where}: {exc}") from exc
    return digest.hexdigest(), size


def _parse_successor_ply_integer(raw: bytes, where: str) -> int:
    if not raw or any(not 48 <= value <= 57 for value in raw):
        raise SurfacePreviewPublishError(f"{where} must be a canonical non-negative integer")
    try:
        value = int(raw)
    except ValueError as exc:
        raise SurfacePreviewPublishError(f"{where} is not a bounded integer") from exc
    if str(value).encode("ascii") != raw:
        raise SurfacePreviewPublishError(f"{where} must be a canonical non-negative integer")
    return value


def _parse_successor_ply_count(
    line: bytes, prefix: bytes, *, limit: int, where: str
) -> int:
    if not line.startswith(prefix):
        raise SurfacePreviewPublishError(f"{where} has an invalid ASCII PLY header")
    value = _parse_successor_ply_integer(line[len(prefix):], f"{where} count")
    if value <= 0 or value > limit:
        raise SurfacePreviewPublishError(f"{where} count is outside the bounded positive range")
    return value


def _validate_successor_ply(path: Path, where: str) -> dict[str, Any]:
    """Verify the exact bounded ASCII triangular PLY emitted by the successor."""

    try:
        with path.open("rb") as stream:
            encoded = stream.read(MAX_ARTIFACT_BYTES + 1)
    except OSError as exc:
        raise SurfacePreviewPublishError(f"could not read {where}: {exc}") from exc
    if len(encoded) > MAX_ARTIFACT_BYTES:
        raise SurfacePreviewPublishError(f"{where} exceeds {MAX_ARTIFACT_BYTES} bytes")
    if not encoded.endswith(b"\n") or b"\r" in encoded:
        raise SurfacePreviewPublishError(f"{where} is not exact ASCII PLY text")
    lines = encoded[:-1].split(b"\n")
    if len(lines) < 12 or lines[0:2] != [b"ply", b"format ascii 1.0"]:
        raise SurfacePreviewPublishError(f"{where} has an invalid ASCII PLY header")
    if lines[3:9] != [
        b"property float x",
        b"property float y",
        b"property float z",
        b"property float nx",
        b"property float ny",
        b"property float nz",
    ] or lines[10:12] != [b"property list uchar int vertex_indices", b"end_header"]:
        raise SurfacePreviewPublishError(f"{where} has an unsupported ASCII PLY property schema")
    vertex_count = _parse_successor_ply_count(
        lines[2], b"element vertex ", limit=MAX_SUCCESSOR_PLY_VERTICES, where=f"{where} vertex"
    )
    face_count = _parse_successor_ply_count(
        lines[9], b"element face ", limit=MAX_SUCCESSOR_PLY_FACES, where=f"{where} face"
    )
    expected_line_count = 12 + vertex_count + face_count
    if len(lines) != expected_line_count:
        raise SurfacePreviewPublishError(f"{where} contains extra, trailing, or missing records")

    vertices: list[tuple[float, float, float, float, float, float]] = []
    for index in range(vertex_count):
        record_where = f"{where} vertex[{index}]"
        fields = lines[12 + index].split()
        if len(fields) != 6:
            raise SurfacePreviewPublishError(f"{record_where} must contain six numeric values")
        try:
            values = tuple(float(field.decode("ascii")) for field in fields)
        except (UnicodeDecodeError, ValueError) as exc:
            raise SurfacePreviewPublishError(f"{record_where} is not a numeric six-value record") from exc
        if not all(math.isfinite(value) for value in values):
            raise SurfacePreviewPublishError(f"{record_where} contains a non-finite value")
        normal_norm_squared = math.fsum(value * value for value in values[3:])
        if (
            not math.isfinite(normal_norm_squared)
            or normal_norm_squared <= SUCCESSOR_PLY_MIN_NORMAL_LENGTH ** 2
        ):
            raise SurfacePreviewPublishError(
                f"{record_where} contains a zero or unusable normal"
            )
        vertices.append(values)

    xyz_vertices = [values[:3] for values in vertices]
    reference = tuple(
        math.fsum(vertex[axis] for vertex in xyz_vertices) / vertex_count
        for axis in range(3)
    )
    centered_vertices = [
        tuple(vertex[axis] - reference[axis] for axis in range(3))
        for vertex in xyz_vertices
    ]
    if not all(math.isfinite(value) for vertex in centered_vertices for value in vertex):
        raise SurfacePreviewPublishError(f"{where} cannot be centered into finite coordinates")
    coordinate_scale = max(
        abs(value) for vertex in centered_vertices for value in vertex
    )
    scale_cubed = coordinate_scale * coordinate_scale * coordinate_scale
    if not math.isfinite(scale_cubed) or coordinate_scale <= 0.0:
        raise SurfacePreviewPublishError(f"{where} has no finite positive enclosed volume")

    parent = list(range(vertex_count))
    rank = [0] * vertex_count
    component_count = vertex_count

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        nonlocal component_count
        left_root = find(left)
        right_root = find(right)
        if left_root == right_root:
            return
        if rank[left_root] < rank[right_root]:
            left_root, right_root = right_root, left_root
        parent[right_root] = left_root
        if rank[left_root] == rank[right_root]:
            rank[left_root] += 1
        component_count -= 1

    faces: list[tuple[int, int, int]] = []
    face_keys: set[tuple[int, int, int]] = set()
    edge_incidence: dict[tuple[int, int], tuple[int, int]] = {}
    edge_faces: dict[tuple[int, int], list[int]] = {}
    for index in range(face_count):
        record_where = f"{where} face[{index}]"
        fields = lines[12 + vertex_count + index].split()
        if len(fields) != 4 or fields[0] != b"3":
            raise SurfacePreviewPublishError(f"{record_where} must be triangular ASCII PLY data")
        try:
            indices = tuple(
                _parse_successor_ply_integer(field, f"{record_where} index")
                for field in fields[1:]
            )
        except SurfacePreviewPublishError:
            raise
        if any(value >= vertex_count for value in indices):
            raise SurfacePreviewPublishError(f"{record_where} contains an out-of-range index")
        if len(set(indices)) != 3:
            raise SurfacePreviewPublishError(f"{record_where} contains duplicate indices")
        face_key = tuple(sorted(indices))
        if face_key in face_keys:
            raise SurfacePreviewPublishError(f"{record_where} is a duplicate face independent of winding")
        face_keys.add(face_key)
        faces.append(indices)
        first, second, third = (centered_vertices[value] for value in indices)
        edge_one = (second[0] - first[0], second[1] - first[1], second[2] - first[2])
        edge_two = (third[0] - first[0], third[1] - first[1], third[2] - first[2])
        cross = (
            edge_one[1] * edge_two[2] - edge_one[2] * edge_two[1],
            edge_one[2] * edge_two[0] - edge_one[0] * edge_two[2],
            edge_one[0] * edge_two[1] - edge_one[1] * edge_two[0],
        )
        cross_norm_squared = sum(value * value for value in cross)
        if not math.isfinite(cross_norm_squared) or cross_norm_squared <= 1.0e-28:
            raise SurfacePreviewPublishError(f"{record_where} is degenerate")
        union(indices[0], indices[1])
        union(indices[1], indices[2])
        union(indices[2], indices[0])
        for left, right in (
            (indices[0], indices[1]),
            (indices[1], indices[2]),
            (indices[2], indices[0]),
        ):
            edge = (left, right) if left < right else (right, left)
            direction = 1 if (left, right) == edge else -1
            previous = edge_incidence.get(edge)
            edge_faces.setdefault(edge, []).append(index)
            incidence = 1 if previous is None else previous[0] + 1
            if incidence > 2:
                raise SurfacePreviewPublishError(f"{where} has an edge incident to more than two faces")
            if previous is not None and previous[1] == direction:
                raise SurfacePreviewPublishError(
                    f"{where} has inconsistent face orientation: each edge must be traversed in opposite directions"
                )
            edge_incidence[edge] = (incidence, direction if previous is None else previous[1])

    if any(incidence != 2 for incidence, _direction in edge_incidence.values()):
        raise SurfacePreviewPublishError(f"{where} is not watertight: every edge must have two incident faces")
    if component_count != 1:
        raise SurfacePreviewPublishError(f"{where} must contain exactly one connected component")
    face_neighbors: list[set[int]] = [set() for _ in faces]
    for incident in edge_faces.values():
        if len(incident) != 2:
            raise SurfacePreviewPublishError(f"{where} has a non-manifold edge")
        left, right = incident
        face_neighbors[left].add(right)
        face_neighbors[right].add(left)
    pending_faces = [0]
    visited_faces: set[int] = set()
    while pending_faces:
        current = pending_faces.pop()
        if current in visited_faces:
            continue
        visited_faces.add(current)
        pending_faces.extend(face_neighbors[current] - visited_faces)
    if len(visited_faces) != face_count:
        raise SurfacePreviewPublishError(f"{where} contains shells connected only at vertices")
    vertex_links: list[dict[int, set[int]]] = [{} for _ in range(vertex_count)]
    for first, second, third in faces:
        for center, left, right in (
            (first, second, third),
            (second, third, first),
            (third, first, second),
        ):
            vertex_links[center].setdefault(left, set()).add(right)
            vertex_links[center].setdefault(right, set()).add(left)
    for link in vertex_links:
        if not link or any(len(neighbors) != 2 for neighbors in link.values()):
            raise SurfacePreviewPublishError(f"{where} has a non-manifold vertex link")
        pending = [next(iter(link))]
        visited: set[int] = set()
        while pending:
            current = pending.pop()
            if current in visited:
                continue
            visited.add(current)
            pending.extend(link[current] - visited)
        if len(visited) != len(link):
            raise SurfacePreviewPublishError(f"{where} has a disconnected vertex link")
    signed_six_volume = math.fsum(
        first[0] * (second[1] * third[2] - second[2] * third[1])
        + first[1] * (second[2] * third[0] - second[0] * third[2])
        + first[2] * (second[0] * third[1] - second[1] * third[0])
        for first, second, third in (
            (centered_vertices[a], centered_vertices[b], centered_vertices[c])
            for a, b, c in faces
        )
    )
    if not math.isfinite(signed_six_volume):
        raise SurfacePreviewPublishError(f"{where} has a non-finite signed volume")
    if signed_six_volume < 0.0:
        raise SurfacePreviewPublishError(
            f"{where} has globally reversed winding; expected canonical outward orientation"
        )
    enclosed_volume = signed_six_volume / 6.0
    volume_tolerance = max(
        scale_cubed * SUCCESSOR_PLY_VOLUME_RELATIVE_TOLERANCE,
        math.ulp(scale_cubed) * SUCCESSOR_PLY_VOLUME_ULP_MULTIPLIER,
    )
    if not math.isfinite(enclosed_volume) or enclosed_volume <= volume_tolerance:
        raise SurfacePreviewPublishError(f"{where} has no finite positive enclosed volume")
    return {
        "vertex_count": vertex_count,
        "face_count": face_count,
        "component_count": component_count,
        "watertight": True,
        "finite_vertices": True,
        "finite_normals": True,
        "valid_indices": True,
    }


def _validate_successor_ply_metrics(
    ply_metrics: dict[str, Any], metrics: dict[str, Any], where: str
) -> None:
    if (
        type(metrics.get("vertex_count")) is not int
        or metrics.get("vertex_count") != ply_metrics["vertex_count"]
        or type(metrics.get("face_count")) is not int
        or metrics.get("face_count") != ply_metrics["face_count"]
        or type(metrics.get("component_count")) is not int
        or metrics.get("component_count") != 1
        or metrics.get("watertight") is not True
        or metrics.get("finite_vertices") is not True
        or metrics.get("finite_normals") is not True
        or metrics.get("valid_indices") is not True
    ):
        raise SurfacePreviewPublishError(f"{where}.metrics topology does not match the validated successor PLY")


def _validate_component_visualization_metrics(
    metrics: dict[str, Any],
    *,
    allowed_owners: list[dict[str, Any]],
    expected_component_count: int,
    expected_recipe_counts: dict[str, int],
    where: str,
) -> None:
    """Validate bounded component claims without becoming a second evaluator."""

    # Generator tests bind actual evaluator/bounds identity; this publisher
    # validates bounded artifact claims and provenance, but does not reimplement
    # NumPy/SciPy geometry or prove pixels.
    prefix = f"{where}.component visualization"

    def fail(message: str) -> None:
        raise SurfacePreviewPublishError(f"{prefix} {message}")

    visualization = metrics.get("component_visualization")
    if not isinstance(visualization, dict):
        fail("metadata is missing or not an object")
    expected_fields = set(EXPECTED_COMPONENT_VISUALIZATION_METRICS) | {"component_count", "components"}
    if set(visualization) != expected_fields:
        fail("metadata has unknown or missing fields")
    for key, expected in EXPECTED_COMPONENT_VISUALIZATION_METRICS.items():
        if visualization.get(key) != expected:
            fail(f"metadata.{key} does not match the fixed configuration")
    if type(visualization.get("component_count")) is not int or visualization["component_count"] != expected_component_count:
        fail(f"metadata.component_count must be exactly {expected_component_count}")

    components = visualization.get("components")
    if not isinstance(components, list) or len(components) > 64 or len(components) != expected_component_count:
        fail(f"metadata.components must contain exactly {expected_component_count} entries")
    if len(expected_recipe_counts) > 64 or any(
        not isinstance(recipe, str) or not recipe or len(recipe) > 256 or type(count) is not int or count < 1
        for recipe, count in expected_recipe_counts.items()
    ):
        fail("expected recipe inventory is not bounded")
    if sum(expected_recipe_counts.values()) != expected_component_count:
        fail("expected recipe inventory count is inconsistent")

    allowed_owner_keys: set[str] = set()
    for index, owner in enumerate(allowed_owners):
        try:
            validated_owner = _validate_address(owner, f"{prefix}.allowed_owner[{index}]")
        except SurfacePreviewPublishError as exc:
            fail(str(exc))
        allowed_owner_keys.add(json.dumps(validated_owner, sort_keys=True, separators=(",", ":")))
    if not allowed_owner_keys or len(allowed_owner_keys) > 64:
        fail("allowed source-owner inventory is not bounded")

    recipe_counts: dict[str, int] = {}
    for index, component in enumerate(components):
        component_where = f"{prefix}.components[{index}]"
        if not isinstance(component, dict) or set(component) != {"source_owner", "recipe", "bounds"}:
            fail(f"{component_where} has unknown or missing fields")
        owner = component.get("source_owner")
        try:
            validated_owner = _validate_address(owner, f"{component_where}.source_owner")
        except SurfacePreviewPublishError as exc:
            fail(str(exc))
        owner_key = json.dumps(validated_owner, sort_keys=True, separators=(",", ":"))
        if owner_key not in allowed_owner_keys:
            fail(f"{component_where}.source_owner is not an allowed validated source owner")
        recipe = component.get("recipe")
        if not isinstance(recipe, str) or not recipe or len(recipe) > 256:
            fail(f"{component_where}.recipe is not a bounded string")
        recipe_counts[recipe] = recipe_counts.get(recipe, 0) + 1
        bounds = component.get("bounds")
        if not isinstance(bounds, dict) or set(bounds) != {"min", "max"}:
            fail(f"{component_where}.bounds has unknown or missing fields")
        component_lower, component_upper = bounds["min"], bounds["max"]
        if not isinstance(component_lower, list) or not isinstance(component_upper, list) or len(component_lower) != 3 or len(component_upper) != 3:
            fail(f"{component_where}.bounds must contain finite ordered triples")
        try:
            component_lower = [_finite_number(value, f"{component_where}.bounds.min[{axis}]") for axis, value in enumerate(component_lower)]
            component_upper = [_finite_number(value, f"{component_where}.bounds.max[{axis}]") for axis, value in enumerate(component_upper)]
        except SurfacePreviewPublishError as exc:
            fail(str(exc))
        if any(left >= right for left, right in zip(component_lower, component_upper)):
            fail(f"{component_where}.bounds must be ordered")
        if any(abs(value) > MAX_COMPONENT_BOUND_ABS for value in component_lower + component_upper):
            fail(
                f"{component_where}.bounds exceed the absolute coordinate limit "
                f"{MAX_COMPONENT_BOUND_ABS}"
            )
    if recipe_counts != expected_recipe_counts:
        fail("metadata recipe histogram does not match the exact current component inventory")


def _evidence_fields(prefix: str) -> set[str]:
    return {
        f"{prefix}_{SOURCE_EVIDENCE_COMPRESSION}_base64",
        f"{prefix}_encoding",
        f"{prefix}_transfer",
        f"{prefix}_compression",
        f"{prefix}_bytes",
        f"{prefix}_sha256",
    }


def _exact_evidence_metadata_limit(*, prefix: str, max_bytes: int) -> int:
    """Bound one evidence carrier from its raw byte ceiling and encoding."""

    # Retain the previous bounded carrier ceiling after changing the owned
    # codec.  An XZ payload that exceeds this secondary bound fails closed; the
    # raw byte ceiling and the final 12 KiB subject-context JSON limit remain
    # independently enforced; ordinary metadata remains capped at 8 KiB.
    compressed_bytes = (
        max_bytes
        + (max_bytes >> 12)
        + (max_bytes >> 14)
        + (max_bytes >> 25)
        + 13
    )
    encoded_bytes = 4 * ((compressed_bytes + 2) // 3)
    fixed_carrier = {
        f"{prefix}_{SOURCE_EVIDENCE_COMPRESSION}_base64": "",
        f"{prefix}_encoding": SOURCE_EVIDENCE_ENCODING,
        f"{prefix}_transfer": SOURCE_EVIDENCE_TRANSFER,
        f"{prefix}_compression": SOURCE_EVIDENCE_COMPRESSION,
        f"{prefix}_bytes": max_bytes,
        f"{prefix}_sha256": "0" * (hashlib.sha256().digest_size * 2),
    }
    return len(
        json.dumps(fixed_carrier, allow_nan=False, ensure_ascii=False)
    ) + encoded_bytes


def _compact_canonical_json(value: Any) -> str:
    """Encode an internal handoff deterministically without display whitespace."""

    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"


def _read_exact_evidence(
    path: Path, *, prefix: str, max_bytes: int, where: str
) -> dict[str, Any]:
    """Read one exact bounded UTF-8 payload into the review evidence carrier."""

    if path.is_symlink() or not path.is_file():
        raise SurfacePreviewPublishError(f"{where} must be a regular non-symlink file")
    try:
        with path.open("rb") as stream:
            size = os.fstat(stream.fileno()).st_size
            if size > max_bytes:
                raise SurfacePreviewPublishError(f"{where} exceeds {max_bytes} bytes")
            raw = stream.read(max_bytes + 1)
    except SurfacePreviewPublishError:
        raise
    except OSError as exc:
        raise SurfacePreviewPublishError(f"could not read {where}: {exc}") from exc
    if len(raw) != size or len(raw) > max_bytes:
        raise SurfacePreviewPublishError(f"{where} changed or exceeds its byte limit")
    try:
        text = raw.decode(SOURCE_EVIDENCE_ENCODING)
    except UnicodeDecodeError as exc:
        raise SurfacePreviewPublishError(f"{where} cannot be retained as UTF-8 evidence") from exc
    if text.encode(SOURCE_EVIDENCE_ENCODING) != raw:
        raise SurfacePreviewPublishError(f"{where} UTF-8 evidence is not byte-exact")
    return {
        f"{prefix}_{SOURCE_EVIDENCE_COMPRESSION}_base64": base64.b64encode(
            lzma.compress(
                raw,
                format=lzma.FORMAT_XZ,
                check=lzma.CHECK_CRC64,
                preset=9 | lzma.PRESET_EXTREME,
            )
        ).decode("ascii"),
        f"{prefix}_encoding": SOURCE_EVIDENCE_ENCODING,
        f"{prefix}_transfer": SOURCE_EVIDENCE_TRANSFER,
        f"{prefix}_compression": SOURCE_EVIDENCE_COMPRESSION,
        f"{prefix}_bytes": len(raw),
        f"{prefix}_sha256": hashlib.sha256(raw).hexdigest(),
    }


def _decode_exact_evidence(
    value: Any, *, prefix: str, max_bytes: int, where: str
) -> bytes:
    """Recover one bounded exact payload from its review binding."""

    if not isinstance(value, dict):
        raise SurfacePreviewPublishError(f"{where} must be an object")
    encoded = value.get(f"{prefix}_{SOURCE_EVIDENCE_COMPRESSION}_base64")
    if not isinstance(encoded, str):
        raise SurfacePreviewPublishError(f"{where} has an invalid Base64 payload")
    try:
        compressed = base64.b64decode(encoded.encode("ascii"), validate=True)
    except (UnicodeEncodeError, ValueError) as exc:
        raise SurfacePreviewPublishError(f"{where} has an invalid Base64 payload") from exc
    try:
        decoder = lzma.LZMADecompressor(
            format=lzma.FORMAT_XZ, memlimit=MAX_LZMA_MEMORY_BYTES
        )
        raw = decoder.decompress(compressed, max_bytes + 1)
    except (lzma.LZMAError, MemoryError) as exc:
        raise SurfacePreviewPublishError(
            f"{where} has invalid compressed bytes or exceeds decoder resource limits"
        ) from exc
    if (
        len(raw) > max_bytes
        or decoder.unused_data
        or not decoder.eof
    ):
        raise SurfacePreviewPublishError(f"{where} compressed bytes are not one bounded stream")
    try:
        text = raw.decode(SOURCE_EVIDENCE_ENCODING)
    except UnicodeDecodeError as exc:
        raise SurfacePreviewPublishError(f"{where} is not valid UTF-8 text") from exc
    if text.encode(SOURCE_EVIDENCE_ENCODING) != raw:
        raise SurfacePreviewPublishError(f"{where} UTF-8 payload is not byte-exact")
    return raw


def _validate_exact_evidence(
    value: Any, *, prefix: str, max_bytes: int, where: str
) -> dict[str, Any]:
    """Validate one lossless payload binding before it enters review.json."""

    if not isinstance(value, dict) or not _evidence_fields(prefix) <= set(value):
        raise SurfacePreviewPublishError(f"{where} is missing its exact UTF-8 binding")
    encoding = value.get(f"{prefix}_encoding")
    transfer = value.get(f"{prefix}_transfer")
    compression = value.get(f"{prefix}_compression")
    byte_count = value.get(f"{prefix}_bytes")
    digest = value.get(f"{prefix}_sha256")
    if (
        encoding != SOURCE_EVIDENCE_ENCODING
        or transfer != SOURCE_EVIDENCE_TRANSFER
        or compression != SOURCE_EVIDENCE_COMPRESSION
    ):
        raise SurfacePreviewPublishError(f"{where} has an invalid encoding declaration")
    if type(byte_count) is not int or not 0 <= byte_count <= max_bytes:
        raise SurfacePreviewPublishError(f"{where} has an invalid byte count")
    if (
        not isinstance(digest, str)
        or len(digest) != hashlib.sha256().digest_size * 2
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        raise SurfacePreviewPublishError(f"{where} has an invalid SHA-256")
    try:
        common._metadata(
            value,
            where,
            max_len=_exact_evidence_metadata_limit(
                prefix=prefix, max_bytes=max_bytes
            ),
        )
    except ValidationError as exc:
        raise SurfacePreviewPublishError(str(exc)) from exc
    raw = _decode_exact_evidence(
        value, prefix=prefix, max_bytes=max_bytes, where=where
    )
    if len(raw) != byte_count or hashlib.sha256(raw).hexdigest() != digest:
        raise SurfacePreviewPublishError(f"{where} does not bind its exact source bytes")
    return value


def _read_input_evidence(path: Path) -> dict[str, Any]:
    exact = _read_exact_evidence(
        path,
        prefix=INPUT_EVIDENCE_PREFIX,
        max_bytes=ORDINARY_SOURCE_BYTES,
        where="producer input",
    )
    return {
        "input_body_document_encoding": exact["input_body_document_encoding"],
        "input_body_document_bytes": exact["input_body_document_bytes"],
        "input_body_document_sha256": exact["input_body_document_sha256"],
    }


def _validate_input_evidence(
    value: Any, where: str = "source evidence", *, max_len: int = common.MAX_STRING
) -> dict[str, Any]:
    if not isinstance(value, dict) or not INPUT_EVIDENCE_FIELDS <= set(value):
        raise SurfacePreviewPublishError(f"{where} is missing its input-source binding")
    if value.get("input_body_document_encoding") != SOURCE_EVIDENCE_ENCODING:
        raise SurfacePreviewPublishError(f"{where} has an invalid input encoding")
    byte_count = value.get("input_body_document_bytes")
    digest = value.get("input_body_document_sha256")
    if type(byte_count) is not int or not 0 <= byte_count <= ORDINARY_SOURCE_BYTES:
        raise SurfacePreviewPublishError(f"{where} has an invalid input byte count")
    if (
        not isinstance(digest, str)
        or len(digest) != hashlib.sha256().digest_size * 2
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        raise SurfacePreviewPublishError(f"{where} has an invalid input SHA-256")
    try:
        common._metadata(value, where, max_len=max_len)
    except ValidationError as exc:
        raise SurfacePreviewPublishError(str(exc)) from exc
    return value


def _read_producer_evidence(path: Path) -> dict[str, Any]:
    return _read_exact_evidence(
        path,
        prefix=PRODUCER_EVIDENCE_PREFIX,
        max_bytes=MAX_STDOUT_BYTES,
        where="producer envelope output",
    )


def _decode_producer_evidence(
    value: Any, where: str = "producer envelope evidence"
) -> bytes:
    return _decode_exact_evidence(
        value,
        prefix=PRODUCER_EVIDENCE_PREFIX,
        max_bytes=MAX_STDOUT_BYTES,
        where=where,
    )


def _validate_producer_evidence(
    value: Any, where: str = "producer envelope evidence"
) -> dict[str, Any]:
    return _validate_exact_evidence(
        value,
        prefix=PRODUCER_EVIDENCE_PREFIX,
        max_bytes=MAX_STDOUT_BYTES,
        where=where,
    )


def _prepare_reviews_root(reviews_root: Path) -> Path:
    """Create and validate the final review root before expensive work."""

    root = reviews_root.absolute()
    try:
        # Only establish the caller-selected final directory.  Do not create
        # missing parents or follow a final-component symlink implicitly.
        root.mkdir(mode=0o755)
    except FileExistsError:
        pass
    except OSError as exc:
        raise SurfacePreviewPublishError(f"could not create reviews root: {exc}") from exc

    root_fd: int | None = None
    probe_name: str | None = None
    try:
        root = common.ensure_root(root)
        common.require_secure_fs_support()
        if os.mkdir not in getattr(os, "supports_dir_fd", set()):
            raise ValidationError("secure visual-review filesystem access lacks descriptor-relative mkdir support")
        # Hold the validated directory itself, and create the owned probe
        # relative to that descriptor.  Reopening `root` by path here would
        # permit a final-component symlink swap to redirect the probe.
        root_fd = _open_directory(None, root, "reviews root")
        for _ in range(8):
            candidate = f".ck-surface-preview-preflight-{secrets.token_hex(16)}"
            try:
                os.mkdir(candidate, 0o700, dir_fd=root_fd)
            except FileExistsError:
                continue
            probe_name = candidate
            break
        if probe_name is None:
            raise OSError("could not allocate a unique reviews-root probe")
        probe_fd = _open_directory(root_fd, probe_name, "reviews root probe")
        os.close(probe_fd)
    except SurfacePreviewPublishError:
        raise
    except (ValidationError, OSError) as exc:
        raise SurfacePreviewPublishError(f"reviews root is not usable: {exc}") from exc
    finally:
        if root_fd is not None:
            if probe_name is not None:
                try:
                    os.rmdir(probe_name, dir_fd=root_fd)
                except OSError:
                    pass
            try:
                os.close(root_fd)
            except OSError:
                pass
    return root


def _regular_artifacts(root: Path) -> tuple[set[str], set[str]]:
    found: set[str] = set()
    directories_found: set[str] = set()
    entries_seen = 0
    regular_bytes = 0
    started = time.monotonic()
    for current, directories, files in os.walk(root, followlinks=False):
        if time.monotonic() - started > MAX_BUNDLE_SCAN_SECONDS:
            raise SurfacePreviewPublishError("surface bundle scan exceeded its time bound")
        current_path = Path(current)
        current_relative = current_path.relative_to(root)
        current_depth = 0 if current_relative == Path(".") else len(current_relative.parts)
        if current_depth > MAX_BUNDLE_SCAN_DEPTH:
            raise SurfacePreviewPublishError("surface bundle contains excessive directory depth")
        for name in directories + files:
            if time.monotonic() - started > MAX_BUNDLE_SCAN_SECONDS:
                raise SurfacePreviewPublishError("surface bundle scan exceeded its time bound")
            entries_seen += 1
            if entries_seen > MAX_BUNDLE_SCAN_ENTRIES:
                raise SurfacePreviewPublishError("surface bundle contains too many entries")
            path = current_path / name
            rel = path.relative_to(root).as_posix()
            if len(path.relative_to(root).parts) > MAX_BUNDLE_SCAN_DEPTH:
                raise SurfacePreviewPublishError("surface bundle contains excessive directory depth")
            if path.is_symlink():
                raise SurfacePreviewPublishError(f"surface bundle contains symlink: {rel}")
            if path.is_file():
                try:
                    regular_bytes += path.stat(follow_symlinks=False).st_size
                except OSError as exc:
                    raise SurfacePreviewPublishError(f"could not inspect surface bundle path: {rel}") from exc
                if regular_bytes > MAX_BUNDLE_SCAN_BYTES:
                    raise SurfacePreviewPublishError("surface bundle contains too many regular-file bytes")
                found.add(rel)
            elif path.is_dir():
                directories_found.add(rel)
            else:
                raise SurfacePreviewPublishError(f"surface bundle contains non-regular path: {rel}")
    return found, directories_found


def _validate_png(path: Path, entry: dict[str, Any], where: str) -> None:
    try:
        encoded = path.read_bytes()
    except OSError as exc:
        raise SurfacePreviewPublishError(f"could not read {where}: {exc}") from exc
    if len(encoded) > MAX_ARTIFACT_BYTES or encoded[:8] != b"\x89PNG\r\n\x1a\n":
        raise SurfacePreviewPublishError(f"{where} is not a bounded PNG")
    offset = 8
    ihdr: bytes | None = None
    idat_parts: list[bytes] = []
    saw_iend = False
    idat_ended = False
    while offset < len(encoded):
        if saw_iend or offset + 12 > len(encoded):
            raise SurfacePreviewPublishError(f"{where} has truncated or trailing PNG data")
        length = struct.unpack(">I", encoded[offset : offset + 4])[0]
        chunk_type = encoded[offset + 4 : offset + 8]
        data_start = offset + 8
        data_end = data_start + length
        crc_end = data_end + 4
        if length > MAX_ARTIFACT_BYTES or crc_end > len(encoded):
            raise SurfacePreviewPublishError(f"{where} has a truncated or oversized PNG chunk")
        chunk_data = encoded[data_start:data_end]
        expected_crc = struct.unpack(">I", encoded[data_end:crc_end])[0]
        actual_crc = zlib.crc32(chunk_data, zlib.crc32(chunk_type)) & 0xFFFFFFFF
        if expected_crc != actual_crc:
            raise SurfacePreviewPublishError(f"{where} has a PNG chunk CRC mismatch")
        if chunk_type not in {b"IHDR", b"IDAT", b"IEND"}:
            raise SurfacePreviewPublishError(f"{where} contains a PNG chunk outside the generated subset")
        if ihdr is None and chunk_type != b"IHDR":
            raise SurfacePreviewPublishError(f"{where} does not begin with IHDR")
        if chunk_type == b"IHDR":
            if ihdr is not None or length != 13 or offset != 8:
                raise SurfacePreviewPublishError(f"{where} has an invalid or duplicate IHDR")
            ihdr = chunk_data
        elif chunk_type == b"IDAT":
            if idat_ended:
                raise SurfacePreviewPublishError(f"{where} has non-contiguous IDAT chunks")
            idat_parts.append(chunk_data)
        else:
            if idat_parts:
                idat_ended = True
            if chunk_type == b"IEND":
                if length != 0:
                    raise SurfacePreviewPublishError(f"{where} has an invalid IEND")
                saw_iend = True
        offset = crc_end
    if ihdr is None or not idat_parts or not saw_iend or offset != len(encoded):
        raise SurfacePreviewPublishError(f"{where} lacks a complete IHDR/IDAT/IEND stream")
    width, height, bit_depth, colour_type, compression, filtering, interlace = struct.unpack(">IIBBBBB", ihdr)
    if not (0 < width <= MAX_PNG_WIDTH and 0 < height <= MAX_PNG_HEIGHT):
        raise SurfacePreviewPublishError(f"{where} dimensions are out of bounds")
    if width != EXPECTED_CANVAS["width"] or height != EXPECTED_CANVAS["height"]:
        raise SurfacePreviewPublishError(f"{where} dimensions do not match the v3 canvas")
    if entry.get("width") != width or entry.get("height") != height:
        raise SurfacePreviewPublishError(f"{where} dimensions do not match inventory")
    mode = entry.get("mode")
    if mode != EXPECTED_CANVAS["mode"]:
        raise SurfacePreviewPublishError(f"{where}.mode does not match the v3 canvas")
    expected_colour_type = {"RGB": 2, "RGBA": 6}.get(mode)
    if expected_colour_type is None:
        raise SurfacePreviewPublishError(f"{where}.mode must be RGB or RGBA")
    if (bit_depth, colour_type, compression, filtering, interlace) != (
        8,
        expected_colour_type,
        0,
        0,
        0,
    ):
        raise SurfacePreviewPublishError(f"{where} IHDR does not match its 8-bit noninterlaced {mode} inventory")
    if entry.get("views") != list(EXPECTED_VIEWS):
        raise SurfacePreviewPublishError(f"{where}.views must be front, side, three-quarter")
    if entry.get("panels_per_view") != 3:
        raise SurfacePreviewPublishError(f"{where}.panels_per_view must be 3")
    bytes_per_pixel = 3 if mode == "RGB" else 4
    row_bytes = width * bytes_per_pixel
    expected_decoded = height * (row_bytes + 1)
    if expected_decoded > MAX_PNG_DECODED_BYTES:
        raise SurfacePreviewPublishError(f"{where} decoded PNG is too large")
    decompressor = zlib.decompressobj()
    try:
        decoded = decompressor.decompress(b"".join(idat_parts), expected_decoded + 1)
        if len(decoded) <= expected_decoded:
            decoded += decompressor.flush(expected_decoded + 1 - len(decoded))
    except zlib.error as exc:
        raise SurfacePreviewPublishError(f"{where} has an invalid IDAT zlib stream: {exc}") from exc
    if (
        len(decoded) != expected_decoded
        or not decompressor.eof
        or decompressor.unused_data
        or decompressor.unconsumed_tail
    ):
        raise SurfacePreviewPublishError(f"{where} IDAT data does not match its declared dimensions")
    if any(decoded[row * (row_bytes + 1)] not in range(5) for row in range(height)):
        raise SurfacePreviewPublishError(f"{where} contains an invalid PNG row filter")


def _finite_json(value: Any, where: str, *, depth: int = 0) -> None:
    """Bound the private guide projection without making it a public schema."""

    if depth > 64:
        raise SurfacePreviewPublishError(f"{where} is too deeply nested")
    if isinstance(value, float) and not math.isfinite(value):
        raise SurfacePreviewPublishError(f"{where} contains a non-finite number")
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise SurfacePreviewPublishError(f"{where} contains a non-text key")
            _finite_json(child, f"{where}.{key}", depth=depth + 1)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _finite_json(child, f"{where}[{index}]", depth=depth + 1)


def _validate_address(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"namespace", "anchors", "kind", "role"}:
        raise SurfacePreviewPublishError(f"{where} is not a source AddressKey")
    if not all(isinstance(value[key], str) and value[key] for key in ("namespace", "kind", "role")):
        raise SurfacePreviewPublishError(f"{where} has invalid AddressKey text")
    anchors = value["anchors"]
    if not isinstance(anchors, list) or not all(isinstance(item, str) and item for item in anchors):
        raise SurfacePreviewPublishError(f"{where}.anchors is invalid")
    return value


def _validate_reference_scale(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"parent", "child", "axis_delta", "squared_length", "source"}:
        raise SurfacePreviewPublishError(f"{where} is invalid")
    parent = _validate_address(value.get("parent"), f"{where}.parent")
    child = _validate_address(value.get("child"), f"{where}.child")
    delta = value.get("axis_delta")
    squared = value.get("squared_length")
    if parent == child or not isinstance(delta, list) or len(delta) != 3 or not all(type(item) is int for item in delta):
        raise SurfacePreviewPublishError(f"{where} has invalid axis reference")
    if type(squared) is not int or squared <= 0 or squared != sum(item * item for item in delta):
        raise SurfacePreviewPublishError(f"{where}.squared_length is inconsistent")
    if value.get("source") != "exact-containment-edge":
        raise SurfacePreviewPublishError(f"{where}.source is invalid")
    return value


def _finite_number(value: Any, where: str) -> float:
    if type(value) not in {int, float}:
        raise SurfacePreviewPublishError(f"{where} must be a finite number")
    try:
        number = float(value)
    except (OverflowError, ValueError) as exc:
        raise SurfacePreviewPublishError(f"{where} must be a finite number") from exc
    if not math.isfinite(number):
        raise SurfacePreviewPublishError(f"{where} must be a finite number")
    return number


def _point(value: Any, where: str) -> list[float]:
    if not isinstance(value, list) or len(value) != 3:
        raise SurfacePreviewPublishError(f"{where} must be a numeric triple")
    return [_finite_number(item, f"{where}[{index}]") for index, item in enumerate(value)]


def _contained(point: list[float], radius: list[float], lower: list[float], upper: list[float], where: str) -> None:
    if any(point[index] - radius[index] < lower[index] or point[index] + radius[index] > upper[index] for index in range(3)):
        raise SurfacePreviewPublishError(f"{where} extends outside shared render bounds")


def _require_axis_aligned_overlap(
    first: dict[str, Any],
    second: dict[str, Any],
    where: str,
) -> None:
    if any(
        abs(first["center"][index] - second["center"][index])
        >= first["radii"][index] + second["radii"][index]
        for index in range(3)
    ):
        raise SurfacePreviewPublishError(f"{where} masses must overlap on every fixed guide axis")


def _mass(value: Any, where: str, lower: list[float], upper: list[float], allowed_controls: set[str]) -> str:
    if not isinstance(value, dict) or set(value) != {"control", "center", "radii"}:
        raise SurfacePreviewPublishError(f"{where} has an invalid mass shape")
    control = value.get("control")
    if control not in allowed_controls:
        raise SurfacePreviewPublishError(f"{where}.control is invalid")
    center = _point(value.get("center"), f"{where}.center")
    radii = _point(value.get("radii"), f"{where}.radii")
    if any(radius <= 0.0 for radius in radii):
        raise SurfacePreviewPublishError(f"{where}.radii must be positive")
    _contained(center, radii, lower, upper, where)
    return control


def _path(value: Any, where: str, lower: list[float], upper: list[float], allowed_controls: set[str], expected_kind: str | None = None) -> str:
    if not isinstance(value, dict) or set(value) not in ({"control", "points", "thickness"}, {"control", "points", "thickness", "path_kind"}):
        raise SurfacePreviewPublishError(f"{where} has an invalid path shape")
    control = value.get("control")
    if control not in allowed_controls:
        raise SurfacePreviewPublishError(f"{where}.control is invalid")
    points = value.get("points")
    if not isinstance(points, list) or len(points) != 2:
        raise SurfacePreviewPublishError(f"{where}.points must contain two triples")
    parsed_points = [_point(point, f"{where}.points[{index}]") for index, point in enumerate(points)]
    if parsed_points[0] == parsed_points[1]:
        raise SurfacePreviewPublishError(f"{where}.points must not be degenerate")
    thickness = value.get("thickness")
    if not isinstance(thickness, list) or len(thickness) not in {1, 2}:
        raise SurfacePreviewPublishError(f"{where}.thickness must contain one or two values")
    parsed_thickness = [_finite_number(item, f"{where}.thickness[{index}]") for index, item in enumerate(thickness)]
    if any(item <= 0.0 for item in parsed_thickness):
        raise SurfacePreviewPublishError(f"{where}.thickness must be positive")
    for point in parsed_points:
        if any(point[index] - max(parsed_thickness) < lower[index] or point[index] + max(parsed_thickness) > upper[index] for index in range(3)):
            raise SurfacePreviewPublishError(f"{where} thickness extends outside shared render bounds")
    if "path_kind" in value:
        path_kind = value["path_kind"]
        if path_kind not in {"capsule", "tapered-segment"}:
            raise SurfacePreviewPublishError(f"{where}.path_kind is invalid")
        if expected_kind is not None and path_kind != expected_kind:
            raise SurfacePreviewPublishError(f"{where}.path_kind does not match its expected primitive")
    elif expected_kind is not None:
        raise SurfacePreviewPublishError(f"{where}.path_kind is missing")
    return control


def _mass_list(value: Any, where: str, lower: list[float], upper: list[float], expected_controls: set[str]) -> None:
    if not isinstance(value, list):
        raise SurfacePreviewPublishError(f"{where} must be an array")
    controls = [_mass(item, f"{where}[{index}]", lower, upper, expected_controls) for index, item in enumerate(value)]
    if len(controls) != len(expected_controls) or set(controls) != expected_controls:
        raise SurfacePreviewPublishError(f"{where} has the wrong controls")


def _path_list(value: Any, where: str, lower: list[float], upper: list[float], expected_controls: set[str], expected_kind: str | None = None) -> None:
    if not isinstance(value, list):
        raise SurfacePreviewPublishError(f"{where} must be an array")
    controls = [_path(item, f"{where}[{index}]", lower, upper, expected_controls, expected_kind=expected_kind) for index, item in enumerate(value)]
    if len(controls) != len(expected_controls) or set(controls) != expected_controls:
        raise SurfacePreviewPublishError(f"{where} has the wrong controls")


def _torso_profile_factors(variant_id: str, owner_role: str) -> tuple[int, int, int]:
    """Return the producer's canonical lateral/anterior/posterior factors."""

    if variant_id == "neutral-v0":
        return (1_000, 1_000, 1_000)
    if variant_id == "broad-soft-v0":
        return (1_200, 1_150, 1_150) if owner_role in {"pelvis", "torso"} else (1_000, 1_000, 1_000)
    if variant_id == "lean-readable-v0":
        return (800, 800, 800)
    if variant_id == "depth-forward-v0":
        return (1_000, 1_300, 1_300) if owner_role == "torso" else (1_000, 1_000, 1_000)
    raise SurfacePreviewPublishError(f"unsupported authored torso profile variant: {variant_id}")


def _address_sort_key(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _identity_key_sort(key_value: tuple[str, str]) -> tuple[Any, ...]:
    address = json.loads(key_value[0])
    return (address["namespace"], tuple(address["anchors"]), address["kind"], address["role"], key_value[1])


def _profile_provenance(source: dict[str, Any], where: str) -> dict[str, str]:
    expected = {
        "source": AUTHORED_TORSO_PROFILE_PROVENANCE_SOURCE,
        "document": source.get("document"),
        "namespace": source.get("namespace"),
    }
    if not all(isinstance(expected[key], str) and expected[key] for key in ("document", "namespace")):
        raise SurfacePreviewPublishError(f"{where} cannot bind source provenance")
    return expected


def _validate_authored_torso_profile(
    producer_payload: dict[str, Any],
) -> dict[str, Any]:
    """Validate and normalize the producer v11 authored profile slice for all consumers.

    The returned object is an internal binding, not a new public artifact
    schema.  Every downstream consumer is keyed by the source AddressKey and
    variant id rather than by the order of an input array.
    """

    where = "provisional-form"
    if not isinstance(producer_payload, dict) or producer_payload.get("format") != common.PROVISIONAL_FORM_V11_FORMAT:
        raise SurfacePreviewPublishError("producer envelope is not provisional-form-preview.v11")
    source = producer_payload.get("source")
    reference_scale = producer_payload.get("reference_scale")
    if not isinstance(source, dict) or set(source) != {"document", "namespace", "resource_profile_id"}:
        raise SurfacePreviewPublishError("producer source identity is invalid")
    if source.get("resource_profile_id") != common.PROVISIONAL_FORM_RESOURCE_PROFILE:
        raise SurfacePreviewPublishError("producer source resource profile is invalid")
    _validate_reference_scale(reference_scale, f"{where}.reference_scale")
    provenance = _profile_provenance(source, f"{where}.authored_torso_profile.provenance")

    profile = producer_payload.get("authored_torso_profile")
    if not isinstance(profile, dict) or set(profile) != {"format", "provenance", "sections"}:
        raise SurfacePreviewPublishError("authored_torso_profile has unknown or missing fields")
    if profile.get("format") != AUTHORED_TORSO_PROFILE_FORMAT or profile.get("provenance") != provenance:
        raise SurfacePreviewPublishError("authored_torso_profile format or provenance is invalid")

    def owner(value: Any, owner_where: str) -> dict[str, Any]:
        return _validate_address(value, owner_where)

    def key(address: dict[str, Any], role: str) -> tuple[str, str]:
        return (_address_sort_key(address), role)

    frames = producer_payload.get("authored_frames")
    if not isinstance(frames, list) or len(frames) != 16:
        raise SurfacePreviewPublishError("v11 authored_frames must contain exactly sixteen owner identity frames")
    frame_map: dict[tuple[str, str], dict[str, Any]] = {}
    for index, raw in enumerate(frames):
        frame_where = f"{where}.authored_frames[{index}]"
        if not isinstance(raw, dict) or set(raw) != {"owner", "role", "transform", "provenance"}:
            raise SurfacePreviewPublishError(f"{frame_where} has an invalid shape")
        frame_owner = owner(raw["owner"], f"{frame_where}.owner")
        role = raw["role"]
        if not isinstance(role, str) or not role:
            raise SurfacePreviewPublishError(f"{frame_where}.role is invalid")
        if role not in {
            common.PROVISIONAL_FORM_SHOULDER_CONTROL_FRAME_ROLE,
            AUTHORED_TORSO_PROFILE_FRAME_ROLE,
            AUTHORED_HEAD_NECK_PROFILE_FRAME_ROLE,
            AUTHORED_ARM_PROFILE_FRAME_ROLE,
            AUTHORED_LEG_PROFILE_FRAME_ROLE,
            AUTHORED_FOOT_PROFILE_FRAME_ROLE,
        }:
            raise SurfacePreviewPublishError(f"{frame_where}.role is not an authored identity frame")
        if raw["provenance"] != provenance:
            raise SurfacePreviewPublishError(f"{frame_where}.provenance is invalid")
        transform = raw["transform"]
        if not isinstance(transform, dict) or set(transform) != {"translation", "rotation_xyzw"}:
            raise SurfacePreviewPublishError(f"{frame_where}.transform is invalid")
        if _point(transform["translation"], f"{frame_where}.transform.translation") != [0.0, 0.0, 0.0]:
            raise SurfacePreviewPublishError(f"{frame_where}.transform must be identity")
        rotation = transform["rotation_xyzw"]
        if not isinstance(rotation, list) or len(rotation) != 4 or any(
            not math.isclose(_finite_number(value, f"{frame_where}.transform.rotation_xyzw"), expected, abs_tol=0.0, rel_tol=0.0)
            for value, expected in zip(rotation, (0.0, 0.0, 0.0, 1.0))
        ):
            raise SurfacePreviewPublishError(f"{frame_where}.transform must be identity")
        frame_key = key(frame_owner, role)
        if frame_key in frame_map:
            raise SurfacePreviewPublishError("authored_frames contains duplicate owner identity frames")
        frame_map[frame_key] = raw
    expected_frame_keys = {
        key({"namespace": source["namespace"], "anchors": [side], "kind": "part", "role": "upper_arm"}, common.PROVISIONAL_FORM_SHOULDER_CONTROL_FRAME_ROLE)
        for side in ("left", "right")
    } | {
        key({"namespace": source["namespace"], "anchors": [], "kind": "part", "role": role}, AUTHORED_TORSO_PROFILE_FRAME_ROLE)
        for role in ("pelvis", "torso")
    } | {
        key({"namespace": source["namespace"], "anchors": [], "kind": "part", "role": role}, AUTHORED_HEAD_NECK_PROFILE_FRAME_ROLE)
        for role in ("neck", "head")
    } | {
        key(
            {"namespace": source["namespace"], "anchors": [side], "kind": "part", "role": owner_role},
            AUTHORED_ARM_PROFILE_FRAME_ROLE,
        )
        for side in AUTHORED_ARM_PROFILE_SIDE_NAMES
        for owner_role in ("upper_arm", "forearm")
    } | {
        key(
            {"namespace": source["namespace"], "anchors": [side], "kind": "part", "role": owner_role},
            AUTHORED_LEG_PROFILE_FRAME_ROLE,
        )
        for side in AUTHORED_LEG_PROFILE_SIDE_NAMES
        for owner_role in ("thigh", "shin")
    } | {
        key(
            {"namespace": source["namespace"], "anchors": [side], "kind": "part", "role": "foot"},
            AUTHORED_FOOT_PROFILE_FRAME_ROLE,
        )
        for side in AUTHORED_FOOT_PROFILE_SIDE_NAMES
    }
    if set(frame_map) != expected_frame_keys or [key(item["owner"], item["role"]) for item in frames] != sorted(expected_frame_keys, key=_identity_key_sort):
        raise SurfacePreviewPublishError("authored_frames do not contain the exact stable v11 owner identity inventory")

    landmarks = producer_payload.get("authored_landmarks")
    if not isinstance(landmarks, list) or len(landmarks) != 43:
        raise SurfacePreviewPublishError("v11 authored_landmarks must contain exactly forty-three axial, head/neck, shoulder, arm, leg, and foot landmarks")
    landmark_map: dict[tuple[str, str], dict[str, Any]] = {}
    for index, raw in enumerate(landmarks):
        landmark_where = f"{where}.authored_landmarks[{index}]"
        if not isinstance(raw, dict) or set(raw) != {"owner", "role", "frame", "position", "provenance"}:
            raise SurfacePreviewPublishError(f"{landmark_where} has an invalid shape")
        landmark_owner = owner(raw["owner"], f"{landmark_where}.owner")
        role = raw["role"]
        if not isinstance(role, str) or not role:
            raise SurfacePreviewPublishError(f"{landmark_where}.role is invalid")
        expected_frame_role = (
            AUTHORED_ARM_PROFILE_FRAME_ROLE
            if role.startswith("form_arm_profile_")
            else AUTHORED_LEG_PROFILE_FRAME_ROLE
            if role.startswith("form_leg_profile_")
            else AUTHORED_FOOT_PROFILE_FRAME_ROLE
            if role.startswith("form_foot_profile_")
            else common.PROVISIONAL_FORM_SHOULDER_CONTROL_FRAME_ROLE
            if landmark_owner["role"] == "upper_arm"
            else AUTHORED_HEAD_NECK_PROFILE_FRAME_ROLE
            if landmark_owner["role"] in {"neck", "head"}
            else AUTHORED_TORSO_PROFILE_FRAME_ROLE
        )
        frame_ref = raw["frame"]
        if not isinstance(frame_ref, dict) or set(frame_ref) != {"owner", "role"} or frame_ref["owner"] != landmark_owner or frame_ref["role"] != expected_frame_role:
            raise SurfacePreviewPublishError(f"{landmark_where}.frame does not bind its owner identity frame")
        if key(landmark_owner, expected_frame_role) not in frame_map:
            raise SurfacePreviewPublishError(f"{landmark_where}.frame references an unlisted owner identity frame")
        position = _point(raw["position"], f"{landmark_where}.position")
        if any(abs(value) > 1.0 for value in position):
            raise SurfacePreviewPublishError(f"{landmark_where}.position is outside the authored control bound")
        if landmark_owner["role"] in {"pelvis", "torso"} and (position[0] != 0.0 or position[2] != 0.0):
            raise SurfacePreviewPublishError(f"{landmark_where}.position must be axial")
        if landmark_owner["role"] in {"neck", "head"} and position[0] != 0.0:
            raise SurfacePreviewPublishError(f"{landmark_where}.position must be axial")
        if role.startswith("form_arm_profile_") and (
            landmark_owner["role"] not in {"upper_arm", "forearm"}
            or position[0] != 0.0
            or position[2] != 0.0
        ):
            raise SurfacePreviewPublishError(f"{landmark_where}.position must be an axial arm profile point")
        if role.startswith("form_leg_profile_") and (
            landmark_owner["role"] not in {"thigh", "shin"}
            or position[0] != 0.0
            or position[2] != 0.0
        ):
            raise SurfacePreviewPublishError(f"{landmark_where}.position must be an axial leg profile point")
        if role.startswith("form_leg_profile_") and not (
            common.PROVISIONAL_FORM_LEG_PROFILE_Y_MIN
            <= position[1]
            <= common.PROVISIONAL_FORM_LEG_PROFILE_Y_MAX
        ):
            raise SurfacePreviewPublishError(
                f"{landmark_where}.position y must be in inclusive "
                f"[{common.PROVISIONAL_FORM_LEG_PROFILE_Y_MIN}, {common.PROVISIONAL_FORM_LEG_PROFILE_Y_MAX}]"
            )
        if role.startswith("form_foot_profile_") and (
            landmark_owner["role"] != "foot"
            or position[0] != 0.0
            or not common.PROVISIONAL_FORM_FOOT_PROFILE_Y_MIN <= position[1] <= common.PROVISIONAL_FORM_FOOT_PROFILE_Y_MAX
            or not common.PROVISIONAL_FORM_FOOT_PROFILE_Z_MIN <= position[2] <= common.PROVISIONAL_FORM_FOOT_PROFILE_Z_MAX
        ):
            raise SurfacePreviewPublishError(
                f"{landmark_where}.position must be [0,y,z] within the authored foot profile bounds"
            )
        if raw["provenance"] != provenance:
            raise SurfacePreviewPublishError(f"{landmark_where}.provenance is invalid")
        landmark_key = key(landmark_owner, role)
        if landmark_key in landmark_map:
            raise SurfacePreviewPublishError("authored_landmarks contains duplicate owner/role keys")
        landmark_map[landmark_key] = raw
    expected_landmark_keys = {
        key({"namespace": source["namespace"], "anchors": [side], "kind": "part", "role": "upper_arm"}, role)
        for side in ("left", "right") for role in common.PROVISIONAL_FORM_SHOULDER_LANDMARK_ROLES
    } | {
        key({"namespace": source["namespace"], "anchors": [], "kind": "part", "role": owner_role}, f"form_torso_profile_{name.replace('-', '_')}")
        for name, owner_role in zip(AUTHORED_TORSO_PROFILE_SECTION_NAMES, AUTHORED_TORSO_PROFILE_OWNER_ROLES)
    } | {
        key({"namespace": source["namespace"], "anchors": [], "kind": "part", "role": owner_role}, f"form_head_neck_profile_{name.replace('-', '_')}")
        for name, owner_role in zip(AUTHORED_HEAD_NECK_PROFILE_SECTION_NAMES, AUTHORED_HEAD_NECK_PROFILE_OWNER_ROLES)
    } | {
        key(
            {"namespace": source["namespace"], "anchors": [side], "kind": "part", "role": owner_role},
            f"form_arm_profile_{name.replace('-', '_')}",
        )
        for side in AUTHORED_ARM_PROFILE_SIDE_NAMES
        for name, owner_role in zip(AUTHORED_ARM_PROFILE_SECTION_NAMES, AUTHORED_ARM_PROFILE_OWNER_ROLES)
    } | {
        key(
            {"namespace": source["namespace"], "anchors": [side], "kind": "part", "role": owner_role},
            f"form_leg_profile_{name.replace('-', '_')}",
        )
        for side in AUTHORED_LEG_PROFILE_SIDE_NAMES
        for name, owner_role in zip(AUTHORED_LEG_PROFILE_SECTION_NAMES, AUTHORED_LEG_PROFILE_OWNER_ROLES)
    } | {
        key(
            {"namespace": source["namespace"], "anchors": [side], "kind": "part", "role": "foot"},
            f"form_foot_profile_{name}",
        )
        for side in AUTHORED_FOOT_PROFILE_SIDE_NAMES
        for name in AUTHORED_FOOT_PROFILE_SECTION_NAMES
    }
    if set(landmark_map) != expected_landmark_keys or [key(item["owner"], item["role"]) for item in landmarks] != sorted(expected_landmark_keys, key=_identity_key_sort):
        raise SurfacePreviewPublishError("authored_landmarks do not contain the exact stable v11 inventory")

    dimensions = producer_payload.get("authored_dimensions")
    if not isinstance(dimensions, list) or not dimensions:
        raise SurfacePreviewPublishError("producer authored_dimensions are missing")
    expected_torso_dimension_keys = {
        key(
            {"namespace": source["namespace"], "anchors": [], "kind": "part", "role": owner_role},
            f"form_torso_profile_{name.replace('-', '_')}_{suffix}",
        )
        for name, owner_role in zip(AUTHORED_TORSO_PROFILE_SECTION_NAMES, AUTHORED_TORSO_PROFILE_OWNER_ROLES)
        for suffix in AUTHORED_TORSO_PROFILE_DIMENSION_SUFFIXES
    }
    expected_head_neck_dimension_keys = {
        key(
            {"namespace": source["namespace"], "anchors": [], "kind": "part", "role": owner_role},
            f"form_head_neck_profile_{name.replace('-', '_')}_{suffix}",
        )
        for name, owner_role in zip(
            AUTHORED_HEAD_NECK_PROFILE_SECTION_NAMES,
            AUTHORED_HEAD_NECK_PROFILE_OWNER_ROLES,
        )
        for suffix in AUTHORED_HEAD_NECK_PROFILE_DIMENSION_SUFFIXES
    }
    expected_arm_dimension_keys = {
        key(
            {"namespace": source["namespace"], "anchors": [side], "kind": "part", "role": owner_role},
            f"form_arm_profile_{name.replace('-', '_')}_{suffix}",
        )
        for side in AUTHORED_ARM_PROFILE_SIDE_NAMES
        for name, owner_role in zip(AUTHORED_ARM_PROFILE_SECTION_NAMES, AUTHORED_ARM_PROFILE_OWNER_ROLES)
        for suffix in AUTHORED_ARM_PROFILE_DIMENSION_SUFFIXES
    }
    expected_leg_dimension_keys = {
        key(
            {"namespace": source["namespace"], "anchors": [side], "kind": "part", "role": owner_role},
            f"form_leg_profile_{name.replace('-', '_')}_{suffix}",
        )
        for side in AUTHORED_LEG_PROFILE_SIDE_NAMES
        for name, owner_role in zip(AUTHORED_LEG_PROFILE_SECTION_NAMES, AUTHORED_LEG_PROFILE_OWNER_ROLES)
        for suffix in AUTHORED_LEG_PROFILE_DIMENSION_SUFFIXES
    }
    expected_foot_dimension_keys = {
        key(
            {"namespace": source["namespace"], "anchors": [side], "kind": "part", "role": "foot"},
            f"form_foot_profile_{name}_{suffix}",
        )
        for side in AUTHORED_FOOT_PROFILE_SIDE_NAMES
        for name in AUTHORED_FOOT_PROFILE_SECTION_NAMES
        for suffix in AUTHORED_FOOT_PROFILE_DIMENSION_SUFFIXES
    }
    dimension_map: dict[tuple[str, str], dict[str, Any]] = {}
    for index, raw in enumerate(dimensions):
        dimension_where = f"{where}.authored_dimensions[{index}]"
        if not isinstance(raw, dict) or set(raw) != {"owner", "role", "value_permille", "provenance"}:
            raise SurfacePreviewPublishError(f"{dimension_where} has an invalid shape")
        dimension_owner = owner(raw["owner"], f"{dimension_where}.owner")
        role = raw["role"]
        value = raw["value_permille"]
        if not isinstance(role, str) or not role or type(value) is not int or raw["provenance"] != provenance:
            raise SurfacePreviewPublishError(f"{dimension_where} is invalid or has wrong provenance")
        dimension_key = key(dimension_owner, role)
        if dimension_key in expected_torso_dimension_keys or dimension_key in expected_head_neck_dimension_keys or dimension_key in expected_arm_dimension_keys or dimension_key in expected_leg_dimension_keys or dimension_key in expected_foot_dimension_keys:
            if not AUTHORED_TORSO_PROFILE_MIN_RADIUS_PERMILLE <= value <= AUTHORED_TORSO_PROFILE_MAX_RADIUS_PERMILLE:
                raise SurfacePreviewPublishError(
                    f"{dimension_where} source torso radius must be an integer in the inclusive range "
                    f"{AUTHORED_TORSO_PROFILE_MIN_RADIUS_PERMILLE}..{AUTHORED_TORSO_PROFILE_MAX_RADIUS_PERMILLE}"
                )
        elif not 1 <= value <= 100_000:
            raise SurfacePreviewPublishError(f"{dimension_where} is invalid or has wrong provenance")
        if dimension_key in dimension_map:
            raise SurfacePreviewPublishError("authored_dimensions contains duplicate owner/role keys")
        dimension_map[dimension_key] = raw
    if not expected_torso_dimension_keys <= set(dimension_map):
        raise SurfacePreviewPublishError("authored_dimensions omit a torso profile radius reference")
    if not expected_head_neck_dimension_keys <= set(dimension_map):
        raise SurfacePreviewPublishError("authored_dimensions omit a head/neck profile radius reference")
    if not expected_arm_dimension_keys <= set(dimension_map):
        raise SurfacePreviewPublishError("authored_dimensions omit an arm profile radius reference")
    if not expected_leg_dimension_keys <= set(dimension_map):
        raise SurfacePreviewPublishError("authored_dimensions omit a leg profile radius reference")
    if not expected_foot_dimension_keys <= set(dimension_map):
        raise SurfacePreviewPublishError("authored_dimensions omit a foot profile radius reference")
    if [key(item["owner"], item["role"]) for item in dimensions] != sorted(dimension_map, key=_identity_key_sort):
        raise SurfacePreviewPublishError("authored_dimensions do not use stable owner/role order")

    raw_sections = profile["sections"]
    if not isinstance(raw_sections, list) or len(raw_sections) != 7:
        raise SurfacePreviewPublishError("authored_torso_profile.sections must contain exactly seven ordered sections")
    torso_lineage: list[dict[str, Any]] = []
    previous_y: float | None = None
    for index, (raw, name, owner_role) in enumerate(zip(raw_sections, AUTHORED_TORSO_PROFILE_SECTION_NAMES, AUTHORED_TORSO_PROFILE_OWNER_ROLES)):
        section_where = f"{where}.authored_torso_profile.sections[{index}]"
        if not isinstance(raw, dict) or set(raw) != {"name", "frame_index", "landmark_index", "dimension_indices", "provenance", "section_index"}:
            raise SurfacePreviewPublishError(f"{section_where} has an invalid indexed shape")
        if (
            raw["name"] != name
            or type(raw["section_index"]) is not int
            or raw["section_index"] != index
            or raw["provenance"] != provenance
        ):
            raise SurfacePreviewPublishError(f"{section_where} name, order, index, or provenance is invalid")
        frame_index = raw["frame_index"]
        landmark_index = raw["landmark_index"]
        if type(frame_index) is not int or not 0 <= frame_index < len(frames) or type(landmark_index) is not int or not 0 <= landmark_index < len(landmarks):
            raise SurfacePreviewPublishError(f"{section_where} index reference is invalid")
        frame = frames[frame_index]
        landmark = landmarks[landmark_index]
        expected_owner = {"namespace": source["namespace"], "anchors": [], "kind": "part", "role": owner_role}
        expected_landmark_role = f"form_torso_profile_{name.replace('-', '_')}"
        if frame["owner"] != expected_owner or frame["role"] != AUTHORED_TORSO_PROFILE_FRAME_ROLE or landmark["owner"] != expected_owner or landmark["role"] != expected_landmark_role or landmark["frame"] != {"owner": expected_owner, "role": AUTHORED_TORSO_PROFILE_FRAME_ROLE}:
            raise SurfacePreviewPublishError(f"{section_where} does not bind its owner frame and axial landmark")
        y = float(landmark["position"][1])
        if previous_y is not None and y <= previous_y:
            raise SurfacePreviewPublishError("authored torso profile axial landmarks are not strictly ordered")
        previous_y = y
        dimension_indices = raw["dimension_indices"]
        if not isinstance(dimension_indices, dict) or set(dimension_indices) != set(AUTHORED_TORSO_PROFILE_RADIUS_AXES):
            raise SurfacePreviewPublishError(f"{section_where}.dimension_indices is invalid")
        dimensions_for_section: list[dict[str, Any]] = []
        for axis, suffix in zip(AUTHORED_TORSO_PROFILE_RADIUS_AXES, AUTHORED_TORSO_PROFILE_DIMENSION_SUFFIXES):
            dimension_index = dimension_indices[axis]
            if type(dimension_index) is not int or not 0 <= dimension_index < len(dimensions):
                raise SurfacePreviewPublishError(f"{section_where}.dimension_indices.{axis} is invalid")
            dimension = dimensions[dimension_index]
            expected_role = f"form_torso_profile_{name.replace('-', '_')}_{suffix}"
            if dimension["owner"] != expected_owner or dimension["role"] != expected_role:
                raise SurfacePreviewPublishError(f"{section_where}.dimension_indices.{axis} does not bind its radius reference")
            dimensions_for_section.append(dimension)
        torso_lineage.append({
            "section_index": index,
            "name": name,
            "owner": expected_owner,
            "frame_index": frame_index,
            "landmark_index": landmark_index,
            "frame": {"owner": expected_owner, "role": AUTHORED_TORSO_PROFILE_FRAME_ROLE},
            "landmark": {"owner": expected_owner, "role": expected_landmark_role, "position": list(landmark["position"])},
            "dimension_indices": dict(dimension_indices),
            "dimensions": [
                {"axis": axis, "role": dimension["role"], "index": dimension_indices[axis], "base_value_permille": dimension["value_permille"]}
                for axis, dimension in zip(AUTHORED_TORSO_PROFILE_RADIUS_AXES, dimensions_for_section)
            ],
        })

    head_profile = producer_payload.get("authored_head_neck_profile")
    if not isinstance(head_profile, dict) or set(head_profile) != {
        "format", "provenance", "sections", "connections"
    }:
        raise SurfacePreviewPublishError(
            "authored_head_neck_profile has unknown or missing fields"
        )
    if (
        head_profile["format"] != AUTHORED_HEAD_NECK_PROFILE_FORMAT
        or head_profile["provenance"] != provenance
    ):
        raise SurfacePreviewPublishError(
            "authored_head_neck_profile format or provenance is invalid"
        )
    connections = head_profile["connections"]
    if not isinstance(connections, list) or len(connections) != len(common.PROVISIONAL_FORM_HEAD_NECK_PROFILE_CONNECTIONS):
        raise SurfacePreviewPublishError(
            "authored_head_neck_profile.connections must contain exactly seven records"
        )
    for index, (connection, expected) in enumerate(
        zip(connections, common.PROVISIONAL_FORM_HEAD_NECK_PROFILE_CONNECTIONS)
    ):
        connection_where = f"{where}.authored_head_neck_profile.connections[{index}]"
        if not isinstance(connection, dict) or set(connection) != {
            "name", "from_section_index", "to_section_index", "route"
        }:
            raise SurfacePreviewPublishError(f"{connection_where} has an invalid shape")
        if (
            connection["name"],
            connection["from_section_index"],
            connection["to_section_index"],
            connection["route"],
        ) != expected:
            raise SurfacePreviewPublishError(
                f"{connection_where} does not match the exact v9 producer connection route"
            )

    raw_head_sections = head_profile["sections"]
    if not isinstance(raw_head_sections, list) or len(raw_head_sections) != len(AUTHORED_HEAD_NECK_PROFILE_SECTION_NAMES):
        raise SurfacePreviewPublishError(
            "authored_head_neck_profile.sections must contain exactly eight ordered sections"
        )
    head_lineage: list[dict[str, Any]] = []
    route_positions: dict[str, list[float]] = {
        "neck vertical": [],
        "cranium vertical": [],
        "forward muzzle": [],
    }
    for index, (raw, name, owner_role) in enumerate(
        zip(
            raw_head_sections,
            AUTHORED_HEAD_NECK_PROFILE_SECTION_NAMES,
            AUTHORED_HEAD_NECK_PROFILE_OWNER_ROLES,
        )
    ):
        section_where = f"{where}.authored_head_neck_profile.sections[{index}]"
        expected_fields = {
            "name", "frame_index", "landmark_index", "dimension_indices",
            "provenance", "section_index",
        }
        if not isinstance(raw, dict) or set(raw) != expected_fields:
            raise SurfacePreviewPublishError(f"{section_where} has an invalid indexed shape")
        if (
            raw["name"] != name
            or type(raw["section_index"]) is not int
            or raw["section_index"] != index
            or raw["provenance"] != provenance
        ):
            raise SurfacePreviewPublishError(
                f"{section_where} name, order, index, or provenance is invalid"
            )
        frame_index = raw["frame_index"]
        landmark_index = raw["landmark_index"]
        expected_owner = {
            "namespace": source["namespace"], "anchors": [], "kind": "part", "role": owner_role
        }
        if (
            type(frame_index) is not int
            or not 0 <= frame_index < len(frames)
            or frame_index != AUTHORED_HEAD_NECK_PROFILE_FRAME_INDICES[owner_role]
            or frames[frame_index]["owner"] != expected_owner
            or frames[frame_index]["role"] != AUTHORED_HEAD_NECK_PROFILE_FRAME_ROLE
            or type(landmark_index) is not int
            or not 0 <= landmark_index < len(landmarks)
            or landmark_index != AUTHORED_HEAD_NECK_PROFILE_LANDMARK_INDICES[index]
        ):
            raise SurfacePreviewPublishError(
                f"{section_where} frame or landmark index does not bind its owner"
            )
        expected_landmark_role = f"form_head_neck_profile_{name.replace('-', '_')}"
        landmark = landmarks[landmark_index]
        if (
            landmark["owner"] != expected_owner
            or landmark["role"] != expected_landmark_role
            or landmark["frame"] != {
                "owner": expected_owner,
                "role": AUTHORED_HEAD_NECK_PROFILE_FRAME_ROLE,
            }
        ):
            raise SurfacePreviewPublishError(
                f"{section_where} does not bind its identity frame and landmark"
            )
        position = landmark["position"]
        if index in (0, 1):
            route_positions["neck vertical"].append(float(position[1]))
        if index in (2, 3, 4):
            route_positions["cranium vertical"].append(float(position[1]))
        if index in (3, 5, 6, 7):
            route_positions["forward muzzle"].append(float(position[2]))
        dimension_indices = raw["dimension_indices"]
        if not isinstance(dimension_indices, dict) or set(dimension_indices) != set(AUTHORED_HEAD_NECK_PROFILE_RADIUS_AXES):
            raise SurfacePreviewPublishError(f"{section_where}.dimension_indices is invalid")
        dimensions_for_section: list[dict[str, Any]] = []
        for axis, suffix in zip(
            AUTHORED_HEAD_NECK_PROFILE_RADIUS_AXES,
            AUTHORED_HEAD_NECK_PROFILE_DIMENSION_SUFFIXES,
        ):
            dimension_index = dimension_indices[axis]
            expected_role = f"form_head_neck_profile_{name.replace('-', '_')}_{suffix}"
            if (
                type(dimension_index) is not int
                or not 0 <= dimension_index < len(dimensions)
                or dimensions[dimension_index]["owner"] != expected_owner
                or dimensions[dimension_index]["role"] != expected_role
            ):
                raise SurfacePreviewPublishError(
                    f"{section_where}.dimension_indices.{axis} does not bind its radius reference"
                )
            dimensions_for_section.append(dimensions[dimension_index])
        head_lineage.append({
            "section_index": index,
            "name": name,
            "owner": expected_owner,
            "frame_index": frame_index,
            "landmark_index": landmark_index,
            "frame": {"owner": expected_owner, "role": AUTHORED_HEAD_NECK_PROFILE_FRAME_ROLE},
            "landmark": {"owner": expected_owner, "role": expected_landmark_role, "position": list(position)},
            "dimension_indices": dict(dimension_indices),
            "dimensions": [
                {
                    "axis": axis,
                    "role": dimension["role"],
                    "index": dimension_indices[axis],
                    "base_value_permille": dimension["value_permille"],
                }
                for axis, dimension in zip(AUTHORED_HEAD_NECK_PROFILE_RADIUS_AXES, dimensions_for_section)
            ],
        })
    for route, positions in route_positions.items():
        if any(left >= right for left, right in zip(positions, positions[1:])):
            raise SurfacePreviewPublishError(
                f"authored head/neck profile landmarks are not strictly ordered on {route} route"
            )

    arm_profile = producer_payload.get("authored_arm_profile")
    if not isinstance(arm_profile, dict) or set(arm_profile) != {"format", "provenance", "sides"}:
        raise SurfacePreviewPublishError("authored_arm_profile has unknown or missing fields")
    if arm_profile["format"] != AUTHORED_ARM_PROFILE_FORMAT or arm_profile["provenance"] != provenance:
        raise SurfacePreviewPublishError("authored_arm_profile format or provenance is invalid")
    arm_sides = arm_profile["sides"]
    if not isinstance(arm_sides, list) or len(arm_sides) != len(AUTHORED_ARM_PROFILE_SIDE_NAMES):
        raise SurfacePreviewPublishError("authored_arm_profile.sides must contain exactly two sides")
    base_arm_lineage: list[dict[str, Any]] = []
    for side_index, (raw_side, side_name) in enumerate(zip(arm_sides, AUTHORED_ARM_PROFILE_SIDE_NAMES)):
        side_where = f"{where}.authored_arm_profile.sides[{side_index}]"
        if not isinstance(raw_side, dict) or set(raw_side) != {"side", "sections"} or raw_side["side"] != side_name:
            raise SurfacePreviewPublishError(f"{side_where} does not use the exact left/right source side order")
        raw_sections = raw_side["sections"]
        if not isinstance(raw_sections, list) or len(raw_sections) != len(AUTHORED_ARM_PROFILE_SECTION_NAMES):
            raise SurfacePreviewPublishError(f"{side_where}.sections must contain exactly five ordered stations")
        sections_lineage: list[dict[str, Any]] = []
        previous_y_by_owner: dict[str, float] = {}
        for section_index, (raw_section, section_name, owner_role) in enumerate(
            zip(raw_sections, AUTHORED_ARM_PROFILE_SECTION_NAMES, AUTHORED_ARM_PROFILE_OWNER_ROLES)
        ):
            section_where = f"{side_where}.sections[{section_index}]"
            expected_fields = {"name", "frame_index", "landmark_index", "dimension_indices", "provenance", "section_index"}
            if not isinstance(raw_section, dict) or set(raw_section) != expected_fields:
                raise SurfacePreviewPublishError(f"{section_where} has an invalid indexed shape")
            if (
                raw_section["name"] != section_name
                or type(raw_section["section_index"]) is not int
                or raw_section["section_index"] != section_index
                or raw_section["provenance"] != provenance
            ):
                raise SurfacePreviewPublishError(f"{section_where} name, order, index, or provenance is invalid")
            frame_index = raw_section["frame_index"]
            landmark_index = raw_section["landmark_index"]
            if (
                type(frame_index) is not int
                or not 0 <= frame_index < len(frames)
                or type(landmark_index) is not int
                or not 0 <= landmark_index < len(landmarks)
            ):
                raise SurfacePreviewPublishError(f"{section_where} index reference is invalid")
            expected_owner = {
                "namespace": source["namespace"], "anchors": [side_name], "kind": "part", "role": owner_role
            }
            expected_landmark_role = f"form_arm_profile_{section_name.replace('-', '_')}"
            frame = frames[frame_index]
            landmark = landmarks[landmark_index]
            if (
                frame["owner"] != expected_owner
                or frame["role"] != AUTHORED_ARM_PROFILE_FRAME_ROLE
                or landmark["owner"] != expected_owner
                or landmark["role"] != expected_landmark_role
                or landmark["frame"] != {"owner": expected_owner, "role": AUTHORED_ARM_PROFILE_FRAME_ROLE}
            ):
                raise SurfacePreviewPublishError(f"{section_where} does not bind its owner frame and axial landmark")
            y = float(landmark["position"][1])
            previous_y = previous_y_by_owner.get(owner_role)
            if previous_y is not None and y >= previous_y:
                raise SurfacePreviewPublishError("authored arm profile landmarks are not strictly ordered on each owner route")
            previous_y_by_owner[owner_role] = y
            dimension_indices = raw_section["dimension_indices"]
            if not isinstance(dimension_indices, dict) or set(dimension_indices) != set(AUTHORED_ARM_PROFILE_RADIUS_AXES):
                raise SurfacePreviewPublishError(f"{section_where}.dimension_indices is invalid")
            dimensions_for_section: list[dict[str, Any]] = []
            for axis, suffix in zip(AUTHORED_ARM_PROFILE_RADIUS_AXES, AUTHORED_ARM_PROFILE_DIMENSION_SUFFIXES):
                dimension_index = dimension_indices[axis]
                expected_role = f"form_arm_profile_{section_name.replace('-', '_')}_{suffix}"
                if (
                    type(dimension_index) is not int
                    or not 0 <= dimension_index < len(dimensions)
                    or dimensions[dimension_index]["owner"] != expected_owner
                    or dimensions[dimension_index]["role"] != expected_role
                ):
                    raise SurfacePreviewPublishError(f"{section_where}.dimension_indices.{axis} does not bind its radius reference")
                dimensions_for_section.append(dimensions[dimension_index])
            sections_lineage.append({
                "section_index": section_index,
                "name": section_name,
                "owner": expected_owner,
                "frame_index": frame_index,
                "landmark_index": landmark_index,
                "frame": {"owner": expected_owner, "role": AUTHORED_ARM_PROFILE_FRAME_ROLE},
                "landmark": {"owner": expected_owner, "role": expected_landmark_role, "position": list(landmark["position"])},
                "dimension_indices": dict(dimension_indices),
                "dimensions": [
                    {"axis": axis, "role": dimension["role"], "index": dimension_indices[axis], "base_value_permille": dimension["value_permille"]}
                    for axis, dimension in zip(AUTHORED_ARM_PROFILE_RADIUS_AXES, dimensions_for_section)
                ],
            })
        base_arm_lineage.append({"side": side_name, "sections": sections_lineage})

    leg_profile = producer_payload.get("authored_leg_profile")
    if not isinstance(leg_profile, dict) or set(leg_profile) != {"format", "provenance", "sides"}:
        raise SurfacePreviewPublishError("authored_leg_profile has unknown or missing fields")
    if leg_profile["format"] != AUTHORED_LEG_PROFILE_FORMAT or leg_profile["provenance"] != provenance:
        raise SurfacePreviewPublishError("authored_leg_profile format or provenance is invalid")
    leg_sides = leg_profile["sides"]
    if not isinstance(leg_sides, list) or [item.get("side") for item in leg_sides if isinstance(item, dict)] != list(AUTHORED_LEG_PROFILE_SIDE_NAMES):
        raise SurfacePreviewPublishError("authored_leg_profile.sides must contain exactly left and right in order")
    base_leg_lineage: list[dict[str, Any]] = []
    for side_index, (raw_side, side_name) in enumerate(zip(leg_sides, AUTHORED_LEG_PROFILE_SIDE_NAMES)):
        side_where = f"{where}.authored_leg_profile.sides[{side_index}]"
        if not isinstance(raw_side, dict) or set(raw_side) != {"side", "sections"} or raw_side["side"] != side_name:
            raise SurfacePreviewPublishError(f"{side_where} does not use the exact left/right source side order")
        raw_sections = raw_side["sections"]
        if not isinstance(raw_sections, list) or len(raw_sections) != len(AUTHORED_LEG_PROFILE_SECTION_NAMES):
            raise SurfacePreviewPublishError(f"{side_where}.sections must contain exactly five ordered stations")
        sections_lineage: list[dict[str, Any]] = []
        previous_y_by_owner: dict[str, float] = {}
        for section_index, (raw_section, section_name, owner_role) in enumerate(
            zip(raw_sections, AUTHORED_LEG_PROFILE_SECTION_NAMES, AUTHORED_LEG_PROFILE_OWNER_ROLES)
        ):
            section_where = f"{side_where}.sections[{section_index}]"
            expected_fields = {"name", "frame_index", "landmark_index", "dimension_indices", "provenance", "section_index"}
            if not isinstance(raw_section, dict) or set(raw_section) != expected_fields:
                raise SurfacePreviewPublishError(f"{section_where} has an invalid indexed shape")
            if (
                raw_section["name"] != section_name
                or type(raw_section["section_index"]) is not int
                or raw_section["section_index"] != section_index
                or raw_section["provenance"] != provenance
            ):
                raise SurfacePreviewPublishError(f"{section_where} name, order, index, or provenance is invalid")
            frame_index = raw_section["frame_index"]
            landmark_index = raw_section["landmark_index"]
            expected_owner = {"namespace": source["namespace"], "anchors": [side_name], "kind": "part", "role": owner_role}
            if (
                type(frame_index) is not int or not 0 <= frame_index < len(frames)
                or type(landmark_index) is not int or not 0 <= landmark_index < len(landmarks)
            ):
                raise SurfacePreviewPublishError(f"{section_where} index reference is invalid")
            expected_landmark_role = f"form_leg_profile_{section_name.replace('-', '_')}"
            frame = frames[frame_index]
            landmark = landmarks[landmark_index]
            if (
                frame["owner"] != expected_owner or frame["role"] != AUTHORED_LEG_PROFILE_FRAME_ROLE
                or landmark["owner"] != expected_owner or landmark["role"] != expected_landmark_role
                or landmark["frame"] != {"owner": expected_owner, "role": AUTHORED_LEG_PROFILE_FRAME_ROLE}
            ):
                raise SurfacePreviewPublishError(f"{section_where} does not bind its owner frame and axial landmark")
            y = float(landmark["position"][1])
            previous_y = previous_y_by_owner.get(owner_role)
            if previous_y is not None and y >= previous_y:
                raise SurfacePreviewPublishError("authored leg profile landmarks are not strictly ordered on each owner route")
            previous_y_by_owner[owner_role] = y
            dimension_indices = raw_section["dimension_indices"]
            if not isinstance(dimension_indices, dict) or set(dimension_indices) != set(AUTHORED_LEG_PROFILE_RADIUS_AXES):
                raise SurfacePreviewPublishError(f"{section_where}.dimension_indices is invalid")
            dimensions_for_section: list[dict[str, Any]] = []
            for axis, suffix in zip(AUTHORED_LEG_PROFILE_RADIUS_AXES, AUTHORED_LEG_PROFILE_DIMENSION_SUFFIXES):
                dimension_index = dimension_indices[axis]
                expected_role = f"form_leg_profile_{section_name.replace('-', '_')}_{suffix}"
                if (
                    type(dimension_index) is not int or not 0 <= dimension_index < len(dimensions)
                    or dimensions[dimension_index]["owner"] != expected_owner
                    or dimensions[dimension_index]["role"] != expected_role
                ):
                    raise SurfacePreviewPublishError(f"{section_where}.dimension_indices.{axis} does not bind its radius reference")
                dimensions_for_section.append(dimensions[dimension_index])
            sections_lineage.append({
                "section_index": section_index,
                "name": section_name,
                "owner": expected_owner,
                "frame_index": frame_index,
                "landmark_index": landmark_index,
                "frame": {"owner": expected_owner, "role": AUTHORED_LEG_PROFILE_FRAME_ROLE},
                "landmark": {"owner": expected_owner, "role": expected_landmark_role, "position": list(landmark["position"])},
                "dimension_indices": dict(dimension_indices),
                "dimensions": [
                    {"axis": axis, "role": dimension["role"], "index": dimension_indices[axis], "base_value_permille": dimension["value_permille"]}
                    for axis, dimension in zip(AUTHORED_LEG_PROFILE_RADIUS_AXES, dimensions_for_section)
                ],
            })
        base_leg_lineage.append({"side": side_name, "sections": sections_lineage})

    foot_profile = producer_payload.get("authored_foot_profile")
    if not isinstance(foot_profile, dict) or set(foot_profile) != {"format", "provenance", "sides"}:
        raise SurfacePreviewPublishError("authored_foot_profile has unknown or missing fields")
    if foot_profile["format"] != AUTHORED_FOOT_PROFILE_FORMAT or foot_profile["provenance"] != provenance:
        raise SurfacePreviewPublishError("authored_foot_profile format or provenance is invalid")
    foot_sides = foot_profile["sides"]
    if not isinstance(foot_sides, list) or [item.get("side") for item in foot_sides if isinstance(item, dict)] != list(AUTHORED_FOOT_PROFILE_SIDE_NAMES):
        raise SurfacePreviewPublishError("authored_foot_profile.sides must contain exactly left and right in order")
    base_foot_lineage: list[dict[str, Any]] = []
    for side_index, (raw_side, side_name) in enumerate(zip(foot_sides, AUTHORED_FOOT_PROFILE_SIDE_NAMES)):
        side_where = f"{where}.authored_foot_profile.sides[{side_index}]"
        if not isinstance(raw_side, dict) or set(raw_side) != {"side", "hock_binding", "sections"} or raw_side["side"] != side_name:
            raise SurfacePreviewPublishError(f"{side_where} does not use the exact left/right source side order")
        expected_hock_binding = {
            "source_profile": "authored_leg_profile",
            "side_index": side_index,
            "section_index": AUTHORED_FOOT_PROFILE_HOCK_SECTION_INDEX,
        }
        if raw_side["hock_binding"] != expected_hock_binding:
            raise SurfacePreviewPublishError(f"{side_where}.hock_binding does not bind the same-side authored leg hock")
        leg_hock = base_leg_lineage[side_index]["sections"][AUTHORED_FOOT_PROFILE_HOCK_SECTION_INDEX]
        if (
            leg_hock["name"] != "hock-endpoint"
            or leg_hock["owner"]["role"] != "shin"
            or leg_hock["owner"]["anchors"] != [side_name]
        ):
            raise SurfacePreviewPublishError(f"{side_where}.hock_binding does not resolve to the same-side shin hock")
        raw_sections = raw_side["sections"]
        if not isinstance(raw_sections, list) or len(raw_sections) != len(AUTHORED_FOOT_PROFILE_SECTION_NAMES):
            raise SurfacePreviewPublishError(f"{side_where}.sections must contain exactly two ordered stations")
        sections_lineage: list[dict[str, Any]] = []
        previous_forward: float | None = None
        for section_index, (raw_section, section_name) in enumerate(zip(raw_sections, AUTHORED_FOOT_PROFILE_SECTION_NAMES)):
            section_where = f"{side_where}.sections[{section_index}]"
            expected_fields = {"name", "frame_index", "landmark_index", "dimension_indices", "provenance", "section_index"}
            if not isinstance(raw_section, dict) or set(raw_section) != expected_fields:
                raise SurfacePreviewPublishError(f"{section_where} has an invalid indexed shape")
            if (
                raw_section["name"] != section_name
                or type(raw_section["section_index"]) is not int
                or raw_section["section_index"] != section_index
                or raw_section["provenance"] != provenance
            ):
                raise SurfacePreviewPublishError(f"{section_where} name, order, index, or provenance is invalid")
            frame_index = raw_section["frame_index"]
            landmark_index = raw_section["landmark_index"]
            expected_owner = {"namespace": source["namespace"], "anchors": [side_name], "kind": "part", "role": "foot"}
            if (
                type(frame_index) is not int or not 0 <= frame_index < len(frames)
                or type(landmark_index) is not int or not 0 <= landmark_index < len(landmarks)
            ):
                raise SurfacePreviewPublishError(f"{section_where} index reference is invalid")
            expected_landmark_role = f"form_foot_profile_{section_name}"
            frame = frames[frame_index]
            landmark = landmarks[landmark_index]
            if (
                frame["owner"] != expected_owner or frame["role"] != AUTHORED_FOOT_PROFILE_FRAME_ROLE
                or landmark["owner"] != expected_owner or landmark["role"] != expected_landmark_role
                or landmark["frame"] != {"owner": expected_owner, "role": AUTHORED_FOOT_PROFILE_FRAME_ROLE}
            ):
                raise SurfacePreviewPublishError(f"{section_where} does not bind its owner frame and foot landmark")
            position = _point(landmark["position"], f"{section_where}.landmark.position")
            if position[0] != 0.0 or not -1.0 <= position[1] <= 0.0 or not 0.0 <= position[2] <= 1.0:
                raise SurfacePreviewPublishError(f"{section_where}.landmark.position is outside the authored foot bounds")
            if previous_forward is not None and position[2] <= previous_forward:
                raise SurfacePreviewPublishError(f"{section_where}.landmark.position must use strict pad-toe forward order")
            previous_forward = position[2]
            dimension_indices = raw_section["dimension_indices"]
            if not isinstance(dimension_indices, dict) or set(dimension_indices) != set(AUTHORED_FOOT_PROFILE_RADIUS_AXES):
                raise SurfacePreviewPublishError(f"{section_where}.dimension_indices is invalid")
            dimensions_for_section: list[dict[str, Any]] = []
            for axis, suffix in zip(AUTHORED_FOOT_PROFILE_RADIUS_AXES, AUTHORED_FOOT_PROFILE_DIMENSION_SUFFIXES):
                dimension_index = dimension_indices[axis]
                expected_role = f"form_foot_profile_{section_name}_{suffix}"
                if (
                    type(dimension_index) is not int or not 0 <= dimension_index < len(dimensions)
                    or dimensions[dimension_index]["owner"] != expected_owner
                    or dimensions[dimension_index]["role"] != expected_role
                ):
                    raise SurfacePreviewPublishError(f"{section_where}.dimension_indices.{axis} does not bind its radius reference")
                dimensions_for_section.append(dimensions[dimension_index])
            sections_lineage.append({
                "section_index": section_index,
                "name": section_name,
                "owner": expected_owner,
                "frame_index": frame_index,
                "landmark_index": landmark_index,
                "frame": {"owner": expected_owner, "role": AUTHORED_FOOT_PROFILE_FRAME_ROLE},
                "landmark": {"owner": expected_owner, "role": expected_landmark_role, "position": list(position)},
                "dimension_indices": dict(dimension_indices),
                "dimensions": [
                    {"axis": axis, "role": dimension["role"], "index": dimension_indices[axis], "base_value_permille": dimension["value_permille"]}
                    for axis, dimension in zip(AUTHORED_FOOT_PROFILE_RADIUS_AXES, dimensions_for_section)
                ],
            })
        base_foot_lineage.append({"side": side_name, "hock_binding": expected_hock_binding, "sections": sections_lineage})

    producer_variants = producer_payload.get("variants")
    if not isinstance(producer_variants, list) or len(producer_variants) != len(EXPECTED_VARIANTS):
        raise SurfacePreviewPublishError("producer variants are not the canonical four variant records")
    variant_bindings: dict[str, dict[str, Any]] = {}
    for raw_variant in producer_variants:
        if not isinstance(raw_variant, dict) or set(raw_variant) != {
            "id", "profile_id", "provenance", "descriptors", "torso_profile", "head_neck_profile", "arm_profile", "leg_profile", "foot_profile"
        }:
            raise SurfacePreviewPublishError("producer variant has unknown or missing v11 fields")
        variant_id = raw_variant["id"]
        if variant_id not in EXPECTED_VARIANTS or variant_id in variant_bindings or raw_variant["profile_id"] != variant_id:
            raise SurfacePreviewPublishError("producer variants have duplicate, unknown, or mismatched ids")
        if raw_variant["provenance"] != {"source": common.PROVISIONAL_FORM_PROVENANCE, "resource_profile_id": common.PROVISIONAL_FORM_RESOURCE_PROFILE, "shape_basis": common.PROVISIONAL_FORM_SHAPE_BASIS}:
            raise SurfacePreviewPublishError(f"producer variant {variant_id} provenance is invalid")
        descriptors = raw_variant["descriptors"]
        if not isinstance(descriptors, list) or len(descriptors) != EXPECTED_GUIDE_COUNTS["owners"]:
            raise SurfacePreviewPublishError(f"producer variant {variant_id} descriptors are invalid")
        descriptor_owners: list[dict[str, Any]] = []
        for descriptor in descriptors:
            if not isinstance(descriptor, dict) or not isinstance(descriptor.get("address"), dict):
                raise SurfacePreviewPublishError(f"producer variant {variant_id} descriptor owner is invalid")
            descriptor_owners.append(_validate_address(descriptor["address"], f"producer variant {variant_id}.descriptor.address"))
        if len({_address_sort_key(item) for item in descriptor_owners}) != len(descriptor_owners):
            raise SurfacePreviewPublishError(f"producer variant {variant_id} descriptor owners are duplicated")
        variant_profile = raw_variant["torso_profile"]
        if not isinstance(variant_profile, dict) or set(variant_profile) != {"format", "source", "provenance", "sections"} or variant_profile["format"] != AUTHORED_TORSO_PROFILE_FORMAT or variant_profile["source"] != "authored_torso_profile" or variant_profile["provenance"] != provenance:
            raise SurfacePreviewPublishError(f"producer variant {variant_id} torso profile identity is invalid")
        scaled_lineage: list[dict[str, Any]] = []
        sections = variant_profile["sections"]
        if not isinstance(sections, list) or len(sections) != len(torso_lineage):
            raise SurfacePreviewPublishError(f"producer variant {variant_id} torso profile section count is invalid")
        for index, (section, base) in enumerate(zip(sections, torso_lineage)):
            section_where = f"producer variant {variant_id}.torso_profile.sections[{index}]"
            if not isinstance(section, dict) or set(section) != {"source_section_index", "name", "position", "lateral_radius_permille", "anterior_radius_permille", "posterior_radius_permille", "scaling", "provenance"}:
                raise SurfacePreviewPublishError(f"{section_where} has an invalid shape")
            factors = _torso_profile_factors(variant_id, base["owner"]["role"])
            if (
                type(section["source_section_index"]) is not int
                or section["source_section_index"] != index
                or section["name"] != base["name"]
                or section["position"] != base["landmark"]["position"]
                or section["provenance"] != provenance
            ):
                raise SurfacePreviewPublishError(f"{section_where} does not bind its source section")
            scaling = section["scaling"]
            if scaling != {"lateral_factor_permille": factors[0], "anterior_factor_permille": factors[1], "posterior_factor_permille": factors[2]}:
                raise SurfacePreviewPublishError(f"{section_where}.scaling is invalid")
            expected_values = tuple(dimension["base_value_permille"] * factor // 1_000 for dimension, factor in zip(base["dimensions"], factors))
            actual_values = tuple(section[f"{axis}_radius_permille"] for axis in AUTHORED_TORSO_PROFILE_RADIUS_AXES)
            if any(
                type(value) is not int
                or not AUTHORED_TORSO_PROFILE_MIN_RADIUS_PERMILLE <= value <= AUTHORED_TORSO_PROFILE_MAX_RADIUS_PERMILLE
                for value in actual_values
            ):
                raise SurfacePreviewPublishError(
                    f"{section_where} projected torso radius must be an integer in the inclusive range "
                    f"{AUTHORED_TORSO_PROFILE_MIN_RADIUS_PERMILLE}..{AUTHORED_TORSO_PROFILE_MAX_RADIUS_PERMILLE}"
                )
            if actual_values != expected_values:
                raise SurfacePreviewPublishError(f"{section_where} radius values do not match authored factors")
            scaled_lineage.append({**base, "scaling": {axis: factor for axis, factor in zip(AUTHORED_TORSO_PROFILE_RADIUS_AXES, factors)}, "scaled_values_permille": {axis: value for axis, value in zip(AUTHORED_TORSO_PROFILE_RADIUS_AXES, actual_values)}})
        variant_head_profile = raw_variant["head_neck_profile"]
        if not isinstance(variant_head_profile, dict) or set(variant_head_profile) != {
            "format", "source", "provenance", "sections", "connections"
        } or variant_head_profile["format"] != AUTHORED_HEAD_NECK_PROFILE_FORMAT or variant_head_profile["source"] != "authored_head_neck_profile" or variant_head_profile["provenance"] != provenance:
            raise SurfacePreviewPublishError(
                f"producer variant {variant_id} head/neck profile identity is invalid"
            )
        if variant_head_profile["connections"] != connections:
            raise SurfacePreviewPublishError(
                f"producer variant {variant_id} head/neck connections do not bind the authored profile"
            )
        variant_head_lineage: list[dict[str, Any]] = []
        variant_head_sections = variant_head_profile["sections"]
        if not isinstance(variant_head_sections, list) or len(variant_head_sections) != len(head_lineage):
            raise SurfacePreviewPublishError(
                f"producer variant {variant_id} head/neck profile section count is invalid"
            )
        for index, (section, base) in enumerate(zip(variant_head_sections, head_lineage)):
            section_where = f"producer variant {variant_id}.head_neck_profile.sections[{index}]"
            expected_fields = {
                "source_section_index", "name", "position",
                "lateral_radius_permille", "up_radius_permille", "forward_radius_permille",
                "scaling", "provenance",
            }
            if not isinstance(section, dict) or set(section) != expected_fields:
                raise SurfacePreviewPublishError(f"{section_where} has an invalid shape")
            factors = common._provisional_form_head_neck_profile_factors(
                variant_id, base["owner"]["role"]
            )
            if (
                type(section["source_section_index"]) is not int
                or section["source_section_index"] != index
                or section["name"] != base["name"]
                or section["position"] != base["landmark"]["position"]
                or section["provenance"] != provenance
            ):
                raise SurfacePreviewPublishError(
                    f"{section_where} does not bind its source section"
                )
            if section["scaling"] != {
                "lateral_factor_permille": factors[0],
                "up_factor_permille": factors[1],
                "forward_factor_permille": factors[2],
            }:
                raise SurfacePreviewPublishError(f"{section_where}.scaling is invalid")
            expected_values = tuple(
                dimension["base_value_permille"] * factor // 1_000
                for dimension, factor in zip(base["dimensions"], factors)
            )
            actual_values = tuple(
                section[f"{axis}_radius_permille"]
                for axis in AUTHORED_HEAD_NECK_PROFILE_RADIUS_AXES
            )
            if actual_values != expected_values or any(
                type(value) is not int
                or not AUTHORED_TORSO_PROFILE_MIN_RADIUS_PERMILLE <= value <= AUTHORED_TORSO_PROFILE_MAX_RADIUS_PERMILLE
                for value in actual_values
            ):
                raise SurfacePreviewPublishError(
                    f"{section_where} radius values do not match authored head/neck factors"
                )
            variant_head_lineage.append({
                **base,
                "scaling": {
                    axis: factor
                    for axis, factor in zip(AUTHORED_HEAD_NECK_PROFILE_RADIUS_AXES, factors)
                },
                "scaled_values_permille": {
                    axis: value
                    for axis, value in zip(AUTHORED_HEAD_NECK_PROFILE_RADIUS_AXES, actual_values)
                },
            })
        variant_arm_profile = raw_variant["arm_profile"]
        if not isinstance(variant_arm_profile, dict) or set(variant_arm_profile) != {
            "format", "source", "provenance", "sides"
        } or variant_arm_profile["format"] != AUTHORED_ARM_PROFILE_FORMAT or variant_arm_profile["source"] != "authored_arm_profile" or variant_arm_profile["provenance"] != provenance:
            raise SurfacePreviewPublishError(f"producer variant {variant_id} arm profile identity is invalid")
        factors = common._provisional_form_arm_profile_factors(variant_id)
        expected_scaling = {
            "lateral_factor_permille": factors[0],
            "up_factor_permille": factors[1],
            "forward_factor_permille": factors[2],
        }
        variant_arm_lineage: list[dict[str, Any]] = []
        variant_arm_sides = variant_arm_profile["sides"]
        if not isinstance(variant_arm_sides, list) or len(variant_arm_sides) != len(base_arm_lineage):
            raise SurfacePreviewPublishError(f"producer variant {variant_id} arm profile side count is invalid")
        for side_index, (raw_side, base_side) in enumerate(zip(variant_arm_sides, base_arm_lineage)):
            section_where = f"producer variant {variant_id}.arm_profile.sides[{side_index}]"
            if not isinstance(raw_side, dict) or set(raw_side) != {"side", "sections"} or raw_side["side"] != base_side["side"]:
                raise SurfacePreviewPublishError(f"{section_where} does not bind its source side")
            raw_sections = raw_side["sections"]
            if not isinstance(raw_sections, list) or len(raw_sections) != len(base_side["sections"]):
                raise SurfacePreviewPublishError(f"{section_where}.sections must contain exactly five source-indexed stations")
            projected_sections: list[dict[str, Any]] = []
            for section_index, (raw_section, base_section) in enumerate(zip(raw_sections, base_side["sections"])):
                item_where = f"{section_where}.sections[{section_index}]"
                expected_fields = {
                    "source_section_index", "name", "position", "lateral_radius_permille",
                    "up_radius_permille", "forward_radius_permille", "scaling", "provenance",
                }
                if not isinstance(raw_section, dict) or set(raw_section) != expected_fields:
                    raise SurfacePreviewPublishError(f"{item_where} has an invalid shape")
                if (
                    type(raw_section["source_section_index"]) is not int
                    or raw_section["source_section_index"] != section_index
                    or raw_section["name"] != base_section["name"]
                    or raw_section["position"] != base_section["landmark"]["position"]
                    or raw_section["scaling"] != expected_scaling
                    or raw_section["provenance"] != provenance
                ):
                    raise SurfacePreviewPublishError(f"{item_where} does not bind its source station or fixed scaling")
                expected_values = tuple(
                    dimension["base_value_permille"] * factor // 1_000
                    for dimension, factor in zip(base_section["dimensions"], factors)
                )
                actual_values = tuple(
                    raw_section[f"{axis}_radius_permille"]
                    for axis in AUTHORED_ARM_PROFILE_RADIUS_AXES
                )
                if actual_values != expected_values or any(
                    type(value) is not int
                    or not AUTHORED_TORSO_PROFILE_MIN_RADIUS_PERMILLE <= value <= AUTHORED_TORSO_PROFILE_MAX_RADIUS_PERMILLE
                    for value in actual_values
                ):
                    raise SurfacePreviewPublishError(f"{item_where} radius values do not match authored arm factors")
                projected_sections.append({
                    **base_section,
                    "scaling": {
                        axis: factor
                        for axis, factor in zip(AUTHORED_ARM_PROFILE_RADIUS_AXES, factors)
                    },
                    "scaled_values_permille": {
                        axis: value
                        for axis, value in zip(AUTHORED_ARM_PROFILE_RADIUS_AXES, actual_values)
                    },
                })
            variant_arm_lineage.append({"side": base_side["side"], "sections": projected_sections})
        variant_leg_profile = raw_variant["leg_profile"]
        if not isinstance(variant_leg_profile, dict) or set(variant_leg_profile) != {
            "format", "source", "provenance", "sides"
        } or variant_leg_profile["format"] != AUTHORED_LEG_PROFILE_FORMAT or variant_leg_profile["source"] != "authored_leg_profile" or variant_leg_profile["provenance"] != provenance:
            raise SurfacePreviewPublishError(f"producer variant {variant_id} leg profile identity is invalid")
        factors = common._provisional_form_leg_profile_factors(variant_id)
        expected_scaling = {
            "lateral_factor_permille": factors[0],
            "up_factor_permille": factors[1],
            "forward_factor_permille": factors[2],
        }
        variant_leg_lineage: list[dict[str, Any]] = []
        variant_leg_sides = variant_leg_profile["sides"]
        if not isinstance(variant_leg_sides, list) or len(variant_leg_sides) != len(base_leg_lineage):
            raise SurfacePreviewPublishError(f"producer variant {variant_id} leg profile side count is invalid")
        for side_index, (raw_side, base_side) in enumerate(zip(variant_leg_sides, base_leg_lineage)):
            section_where = f"producer variant {variant_id}.leg_profile.sides[{side_index}]"
            if not isinstance(raw_side, dict) or set(raw_side) != {"side", "sections"} or raw_side["side"] != base_side["side"]:
                raise SurfacePreviewPublishError(f"{section_where} does not bind its source side")
            raw_sections = raw_side["sections"]
            if not isinstance(raw_sections, list) or len(raw_sections) != len(base_side["sections"]):
                raise SurfacePreviewPublishError(f"{section_where}.sections must contain exactly five source-indexed stations")
            projected_sections: list[dict[str, Any]] = []
            for section_index, (raw_section, base_section) in enumerate(zip(raw_sections, base_side["sections"])):
                item_where = f"{section_where}.sections[{section_index}]"
                expected_fields = {
                    "source_section_index", "name", "position", "lateral_radius_permille",
                    "up_radius_permille", "forward_radius_permille", "scaling", "provenance",
                }
                if not isinstance(raw_section, dict) or set(raw_section) != expected_fields:
                    raise SurfacePreviewPublishError(f"{item_where} has an invalid shape")
                if (
                    type(raw_section["source_section_index"]) is not int
                    or raw_section["source_section_index"] != section_index
                    or raw_section["name"] != base_section["name"]
                    or raw_section["position"] != base_section["landmark"]["position"]
                    or raw_section["scaling"] != expected_scaling
                    or raw_section["provenance"] != provenance
                ):
                    raise SurfacePreviewPublishError(f"{item_where} does not bind its source station or fixed scaling")
                expected_values = tuple(
                    dimension["base_value_permille"] * factor // 1_000
                    for dimension, factor in zip(base_section["dimensions"], factors)
                )
                actual_values = tuple(raw_section[f"{axis}_radius_permille"] for axis in AUTHORED_LEG_PROFILE_RADIUS_AXES)
                if actual_values != expected_values or any(
                    type(value) is not int
                    or not AUTHORED_TORSO_PROFILE_MIN_RADIUS_PERMILLE <= value <= AUTHORED_TORSO_PROFILE_MAX_RADIUS_PERMILLE
                    for value in actual_values
                ):
                    raise SurfacePreviewPublishError(f"{item_where} radius values do not match authored leg factors")
                projected_sections.append({
                    **base_section,
                    "scaling": {axis: factor for axis, factor in zip(AUTHORED_LEG_PROFILE_RADIUS_AXES, factors)},
                    "scaled_values_permille": {axis: value for axis, value in zip(AUTHORED_LEG_PROFILE_RADIUS_AXES, actual_values)},
                })
            variant_leg_lineage.append({"side": base_side["side"], "sections": projected_sections})
        variant_foot_profile = raw_variant["foot_profile"]
        if not isinstance(variant_foot_profile, dict) or set(variant_foot_profile) != {
            "format", "source", "provenance", "sides"
        } or variant_foot_profile["format"] != AUTHORED_FOOT_PROFILE_FORMAT or variant_foot_profile["source"] != "authored_foot_profile" or variant_foot_profile["provenance"] != provenance:
            raise SurfacePreviewPublishError(f"producer variant {variant_id} foot profile identity is invalid")
        factors = common._provisional_form_foot_profile_factors(variant_id)
        expected_scaling = {
            "lateral_factor_permille": factors[0],
            "up_factor_permille": factors[1],
            "forward_factor_permille": factors[2],
        }
        variant_foot_lineage: list[dict[str, Any]] = []
        variant_foot_sides = variant_foot_profile["sides"]
        if not isinstance(variant_foot_sides, list) or len(variant_foot_sides) != len(base_foot_lineage):
            raise SurfacePreviewPublishError(f"producer variant {variant_id} foot profile side count is invalid")
        for side_index, (raw_side, base_side) in enumerate(zip(variant_foot_sides, base_foot_lineage)):
            section_where = f"producer variant {variant_id}.foot_profile.sides[{side_index}]"
            if not isinstance(raw_side, dict) or set(raw_side) != {"side", "hock_binding", "sections"} or raw_side["side"] != base_side["side"] or raw_side["hock_binding"] != base_side["hock_binding"]:
                raise SurfacePreviewPublishError(f"{section_where} does not bind its source side or hock")
            raw_sections = raw_side["sections"]
            if not isinstance(raw_sections, list) or len(raw_sections) != len(base_side["sections"]):
                raise SurfacePreviewPublishError(f"{section_where}.sections must contain exactly two source-indexed stations")
            projected_sections: list[dict[str, Any]] = []
            for section_index, (raw_section, base_section) in enumerate(zip(raw_sections, base_side["sections"])):
                item_where = f"{section_where}.sections[{section_index}]"
                expected_fields = {
                    "source_section_index", "name", "position", "lateral_radius_permille",
                    "up_radius_permille", "forward_radius_permille", "scaling", "provenance",
                }
                if not isinstance(raw_section, dict) or set(raw_section) != expected_fields:
                    raise SurfacePreviewPublishError(f"{item_where} has an invalid shape")
                if (
                    type(raw_section["source_section_index"]) is not int
                    or raw_section["source_section_index"] != section_index
                    or raw_section["name"] != base_section["name"]
                    or raw_section["position"] != base_section["landmark"]["position"]
                    or raw_section["scaling"] != expected_scaling
                    or raw_section["provenance"] != provenance
                ):
                    raise SurfacePreviewPublishError(f"{item_where} does not bind its source station or fixed scaling")
                expected_values = tuple(
                    dimension["base_value_permille"] * factor // 1_000
                    for dimension, factor in zip(base_section["dimensions"], factors)
                )
                actual_values = tuple(raw_section[f"{axis}_radius_permille"] for axis in AUTHORED_FOOT_PROFILE_RADIUS_AXES)
                if actual_values != expected_values or any(
                    type(value) is not int
                    or not AUTHORED_TORSO_PROFILE_MIN_RADIUS_PERMILLE <= value <= AUTHORED_TORSO_PROFILE_MAX_RADIUS_PERMILLE
                    for value in actual_values
                ):
                    raise SurfacePreviewPublishError(f"{item_where} radius values do not match authored foot factors")
                projected_sections.append({
                    **base_section,
                    "scaling": {axis: factor for axis, factor in zip(AUTHORED_FOOT_PROFILE_RADIUS_AXES, factors)},
                    "scaled_values_permille": {axis: value for axis, value in zip(AUTHORED_FOOT_PROFILE_RADIUS_AXES, actual_values)},
                })
            variant_foot_lineage.append({"side": base_side["side"], "hock_binding": base_side["hock_binding"], "sections": projected_sections})
        variant_bindings[variant_id] = {
            "variant_id": variant_id,
            "profile_id": raw_variant["profile_id"],
            "producer_variant_sha256": _source_variant_sha256(raw_variant, f"producer variant {variant_id}"),
            "descriptor_owners": sorted(descriptor_owners, key=_address_sort_key),
            "torso_lineage": scaled_lineage,
            "head_neck_lineage": variant_head_lineage,
            "arm_lineage": variant_arm_lineage,
            "leg_lineage": variant_leg_lineage,
            "foot_lineage": variant_foot_lineage,
        }
    if set(variant_bindings) != set(EXPECTED_VARIANTS):
        raise SurfacePreviewPublishError("producer variants do not contain the exact canonical variant set")
    return {
        "source": {"format": common.PROVISIONAL_FORM_FORMAT, **source},
        "reference_scale": reference_scale,
        "provenance": provenance,
        "top_profile": profile,
        "frames": frame_map,
        "landmarks": landmark_map,
        "dimensions": dimension_map,
        "base_torso_lineage": torso_lineage,
        "base_head_neck_lineage": head_lineage,
        "base_arm_lineage": base_arm_lineage,
        "base_leg_lineage": base_leg_lineage,
        "base_foot_lineage": base_foot_lineage,
        "head_neck_profile": head_profile,
        "variants": variant_bindings,
    }


def _validate_arm_profile_controls(
    arm_profile: Any,
    controls: dict[str, Any],
    lower: list[float],
    upper: list[float],
    *,
    variant_id: str,
    producer_payload: dict[str, Any],
) -> None:
    """Validate v10 guide arm stations against the indexed v11 producer slice."""

    expected_fields = {"format", "status", "provenance", "axes", "sides"}
    if not isinstance(arm_profile, dict) or set(arm_profile) != expected_fields:
        raise SurfacePreviewPublishError("regional guide arm profile controls are invalid")
    profile_context = _validate_authored_torso_profile(producer_payload)
    if (
        arm_profile["format"] != AUTHORED_ARM_PROFILE_FORMAT
        or arm_profile["status"] != "skin-driving arm profile; legacy shoulder supports remain guide-only"
        or arm_profile["provenance"] != profile_context["provenance"]
        or arm_profile["axes"] != {
            "lateral": [1.0, 0.0, 0.0],
            "up": [0.0, 1.0, 0.0],
            "forward": [0.0, 0.0, 1.0],
        }
    ):
        raise SurfacePreviewPublishError("regional guide arm profile identity or axes are invalid")
    sides = arm_profile["sides"]
    if not isinstance(sides, list) or [item.get("side") for item in sides if isinstance(item, dict)] != list(AUTHORED_ARM_PROFILE_SIDE_NAMES):
        raise SurfacePreviewPublishError("regional guide arm profile sides are invalid")
    base_sides = profile_context["base_arm_lineage"]
    projected_sides = profile_context["variants"][variant_id]["arm_lineage"]
    limbs_by_owner = {
        _address_sort_key(item["owner"]): item
        for item in controls["limbs"]
        if isinstance(item, dict) and isinstance(item.get("owner"), dict)
    }
    for side_index, (guide_side, base_side, projected_side) in enumerate(zip(sides, base_sides, projected_sides)):
        where = f"regional-guide.controls.arm_profile.sides[{side_index}]"
        if not isinstance(guide_side, dict) or set(guide_side) != {"side", "sections"} or guide_side["side"] != base_side["side"]:
            raise SurfacePreviewPublishError(f"{where} does not bind its indexed source side")
        guide_sections = guide_side["sections"]
        if not isinstance(guide_sections, list) or len(guide_sections) != len(base_side["sections"]):
            raise SurfacePreviewPublishError(f"{where}.sections must contain exactly five records")
        for section_index, (section, base, projected) in enumerate(zip(guide_sections, base_side["sections"], projected_side["sections"])):
            section_where = f"{where}.sections[{section_index}]"
            section_fields = {
                "name", "section_index", "source_section_index", "frame_index", "landmark_index",
                "owner", "frame", "landmark", "center", "radii", "lateral_radius", "up_radius",
                "forward_radius", "lineage", "consumption",
            }
            if not isinstance(section, dict) or set(section) != section_fields:
                raise SurfacePreviewPublishError(f"{section_where} has an invalid shape")
            if (
                section["name"] != base["name"]
                or section["section_index"] != section_index
                or section["source_section_index"] != section_index
                or section["frame_index"] != base["frame_index"]
                or section["landmark_index"] != base["landmark_index"]
                or section["owner"] != base["owner"]
                or section["frame"] != base["frame"]
                or section["consumption"] != ("skin-driving; elbow seam owned by upper_arm station" if section_index == 2 else "skin-driving")
            ):
                raise SurfacePreviewPublishError(f"{section_where} indexed identity does not match the producer profile")
            expected_landmark = profile_context["landmarks"][
                (_address_sort_key(base["owner"]), base["landmark"]["role"])
            ]
            if section["landmark"] != expected_landmark:
                raise SurfacePreviewPublishError(f"{section_where}.landmark does not match the producer profile")
            center = _point(section["center"], f"{section_where}.center")
            radii = section["radii"]
            if not isinstance(radii, dict) or set(radii) != set(AUTHORED_ARM_PROFILE_RADIUS_AXES):
                raise SurfacePreviewPublishError(f"{section_where}.radii is invalid")
            for axis in AUTHORED_ARM_PROFILE_RADIUS_AXES:
                _finite_number(radii[axis], f"{section_where}.radii.{axis}")
                _finite_number(section[f"{axis}_radius"], f"{section_where}.{axis}_radius")
            limb = limbs_by_owner.get(_address_sort_key(base["owner"]))
            if limb is None or not isinstance(limb.get("sections"), list) or not limb["sections"]:
                raise SurfacePreviewPublishError(f"{section_where} has no matching source limb centerline")
            path_start = limb["sections"][0]["points"][0]
            path_end = limb["sections"][-1]["points"][1]
            local_y = float(base["landmark"]["position"][1])
            expected_center = [
                float(path_start[axis]) - local_y * (float(path_end[axis]) - float(path_start[axis]))
                for axis in range(3)
            ]
            if any(not math.isclose(center[axis], expected_center[axis], rel_tol=0.0, abs_tol=1.0e-12) for axis in range(3)):
                raise SurfacePreviewPublishError(f"{section_where}.center is not projected onto the source limb centerline")
            expected_radii = {
                axis: projected["scaled_values_permille"][axis] / 1000.0
                for axis in AUTHORED_ARM_PROFILE_RADIUS_AXES
            }
            if radii != expected_radii or any(
                not math.isclose(float(section[f"{axis}_radius"]), expected_radii[axis], rel_tol=0.0, abs_tol=1.0e-12)
                for axis in AUTHORED_ARM_PROFILE_RADIUS_AXES
            ):
                raise SurfacePreviewPublishError(f"{section_where}.radii do not bind the variant profile")
            expected_lineage = {
                axis: {
                    "base": dimension["base_value_permille"],
                    "factor": projected["scaling"][axis],
                    "scaled": projected["scaled_values_permille"][axis],
                    "reference": {"owner": base["owner"], "role": dimension["role"], "index": dimension["index"]},
                    "provenance": profile_context["provenance"],
                    "consumed_section": base["name"],
                }
                for axis, dimension in zip(AUTHORED_ARM_PROFILE_RADIUS_AXES, base["dimensions"])
            }
            if section["lineage"] != expected_lineage:
                raise SurfacePreviewPublishError(f"{section_where}.lineage does not bind source dimensions")
            _contained(center, [max(radii.values())] * 3, lower, upper, f"{section_where}.center")
        upper_limb = limbs_by_owner.get(_address_sort_key(guide_sections[2]["owner"]))
        forearm_limb = limbs_by_owner.get(_address_sort_key(guide_sections[3]["owner"]))
        if upper_limb is None or forearm_limb is None:
            raise SurfacePreviewPublishError(f"{where} is missing the source upper-arm or forearm")
        if guide_sections[0]["center"] != upper_limb["sections"][0]["points"][0]:
            raise SurfacePreviewPublishError(f"{where} moved the preserved shoulder attachment")
        if guide_sections[2]["center"] != upper_limb["sections"][-1]["points"][1]:
            raise SurfacePreviewPublishError(f"{where} elbow is not the upper-arm-owned endpoint")
        forearm_start = forearm_limb["sections"][0]["points"][0]
        forearm_end = forearm_limb["sections"][-1]["points"][1]
        expected_midpoint = [
            float(forearm_start[axis]) + 0.5 * (float(forearm_end[axis]) - float(forearm_start[axis]))
            for axis in range(3)
        ]
        if any(not math.isclose(float(guide_sections[3]["center"][axis]), expected_midpoint[axis], rel_tol=0.0, abs_tol=1.0e-12) for axis in range(3)):
            raise SurfacePreviewPublishError(f"{where} forearm midpoint is not on the source centerline")


def _validate_leg_profile_controls(
    leg_profile: Any,
    controls: dict[str, Any],
    lower: list[float],
    upper: list[float],
    *,
    variant_id: str,
    producer_payload: dict[str, Any],
) -> None:
    """Validate the v10 guide's exact bilateral five-station leg routes."""

    expected_fields = {"format", "status", "provenance", "variant_provenance", "axes", "route_topology", "sides"}
    if not isinstance(leg_profile, dict) or set(leg_profile) != expected_fields:
        raise SurfacePreviewPublishError("regional guide leg profile controls are invalid")
    profile_context = _validate_authored_torso_profile(producer_payload)
    if (
        leg_profile["format"] != AUTHORED_LEG_PROFILE_FORMAT
        or leg_profile["status"] != "skin-driving leg profile; knee seam owned by thigh; hock owned by shin"
        or leg_profile["provenance"] != profile_context["provenance"]
        or leg_profile["variant_provenance"] != profile_context["provenance"]
        or leg_profile["axes"] != {
            "lateral": [1.0, 0.0, 0.0],
            "up": [0.0, 1.0, 0.0],
            "forward": [0.0, 0.0, 1.0],
        }
        or leg_profile["route_topology"] != {
            "section_names": list(AUTHORED_LEG_PROFILE_SECTION_NAMES),
            "owner_roles": list(AUTHORED_LEG_PROFILE_OWNER_ROLES),
            "seam": {"name": "knee", "index": 2, "owner_role": "thigh"},
            "endpoint": {"name": "hock-endpoint", "index": 4, "owner_role": "shin"},
        }
    ):
        raise SurfacePreviewPublishError("regional guide leg profile identity or topology is invalid")
    sides = leg_profile["sides"]
    if not isinstance(sides, list) or [item.get("side") for item in sides if isinstance(item, dict)] != list(AUTHORED_LEG_PROFILE_SIDE_NAMES):
        raise SurfacePreviewPublishError("regional guide leg profile sides are invalid")
    base_sides = profile_context["base_leg_lineage"]
    projected_sides = profile_context["variants"][variant_id]["leg_lineage"]
    limbs_by_owner = {
        (_address_sort_key(item["owner"]), item["owner"]["role"]): item
        for item in controls["limbs"]
        if isinstance(item, dict) and isinstance(item.get("owner"), dict)
    }
    for side_index, (guide_side, base_side, projected_side) in enumerate(zip(sides, base_sides, projected_sides)):
        where = f"regional-guide.controls.leg_profile.sides[{side_index}]"
        if not isinstance(guide_side, dict) or set(guide_side) != {"side", "sections"} or guide_side["side"] != base_side["side"]:
            raise SurfacePreviewPublishError(f"{where} does not bind its indexed source side")
        guide_sections = guide_side["sections"]
        if not isinstance(guide_sections, list) or len(guide_sections) != len(base_side["sections"]):
            raise SurfacePreviewPublishError(f"{where}.sections must contain exactly five records")
        for section_index, (section, base, projected) in enumerate(zip(guide_sections, base_side["sections"], projected_side["sections"])):
            section_where = f"{where}.sections[{section_index}]"
            section_fields = {
                "name", "section_index", "source_section_index", "frame_index", "landmark_index",
                "owner", "frame", "landmark", "center", "radii", "lateral_radius", "up_radius",
                "forward_radius", "profile_provenance", "variant_provenance", "lineage", "consumption",
            }
            if not isinstance(section, dict) or set(section) != section_fields:
                raise SurfacePreviewPublishError(f"{section_where} has an invalid shape")
            if (
                section["name"] != base["name"]
                or section["section_index"] != section_index
                or section["source_section_index"] != section_index
                or section["frame_index"] != base["frame_index"]
                or section["landmark_index"] != base["landmark_index"]
                or section["owner"] != base["owner"]
                or section["frame"] != base["frame"]
                or section["profile_provenance"] != profile_context["provenance"]
                or section["variant_provenance"] != profile_context["provenance"]
                or section["consumption"] != ("skin-driving; knee seam owned by thigh station" if section_index == 2 else "skin-driving")
            ):
                raise SurfacePreviewPublishError(f"{section_where} indexed identity does not match the producer profile")
            expected_landmark = profile_context["landmarks"][_address_sort_key(base["owner"]), base["landmark"]["role"]]
            if section["landmark"] != expected_landmark:
                raise SurfacePreviewPublishError(f"{section_where}.landmark does not match the producer profile")
            limb = limbs_by_owner.get((_address_sort_key(base["owner"]), base["owner"]["role"]))
            if limb is None or not isinstance(limb.get("sections"), list) or not limb["sections"]:
                raise SurfacePreviewPublishError(f"{section_where} has no matching source limb centerline")
            path_start = limb["sections"][0]["points"][0]
            path_end = limb["sections"][-1]["points"][1]
            local_y = float(base["landmark"]["position"][1])
            expected_center = [
                float(path_start[axis]) - local_y * (float(path_end[axis]) - float(path_start[axis]))
                for axis in range(3)
            ]
            if section["center"] != expected_center:
                raise SurfacePreviewPublishError(f"{section_where}.center is not the exact source centerline projection")
            radii = section["radii"]
            if not isinstance(radii, dict) or set(radii) != set(AUTHORED_LEG_PROFILE_RADIUS_AXES):
                raise SurfacePreviewPublishError(f"{section_where}.radii is invalid")
            expected_radii = {axis: projected["scaled_values_permille"][axis] / 1000.0 for axis in AUTHORED_LEG_PROFILE_RADIUS_AXES}
            if radii != expected_radii or any(section[f"{axis}_radius"] != expected_radii[axis] for axis in AUTHORED_LEG_PROFILE_RADIUS_AXES):
                raise SurfacePreviewPublishError(f"{section_where}.radii do not bind the variant profile")
            expected_lineage = {
                axis: {
                    "base": dimension["base_value_permille"],
                    "factor": projected["scaling"][axis],
                    "scaled": projected["scaled_values_permille"][axis],
                    "reference": {"owner": base["owner"], "role": dimension["role"], "index": dimension["index"]},
                    "provenance": profile_context["provenance"],
                    "consumed_section": base["name"],
                }
                for axis, dimension in zip(AUTHORED_LEG_PROFILE_RADIUS_AXES, base["dimensions"])
            }
            if section["lineage"] != expected_lineage:
                raise SurfacePreviewPublishError(f"{section_where}.lineage does not bind source dimensions")
            _contained(section["center"], [max(radii.values())] * 3, lower, upper, f"{section_where}.center")

        thigh = limbs_by_owner.get((_address_sort_key(base_sides[side_index]["sections"][0]["owner"]), "thigh"))
        shin = limbs_by_owner.get((_address_sort_key(base_sides[side_index]["sections"][3]["owner"]), "shin"))
        if thigh is None or shin is None:
            raise SurfacePreviewPublishError(f"{where} is missing its thigh or shin consumer")
        thigh_sections = {item["control"]: item for item in thigh["sections"]}
        shin_sections = {item["control"]: item for item in shin["sections"]}
        if set(thigh_sections) != {"pre-joint", "joint"} or set(shin_sections) != {"pre-joint", "joint"}:
            raise SurfacePreviewPublishError(f"{where} has an invalid thigh/shin section inventory")
        centers = [item["center"] for item in guide_sections]
        if (
            thigh_sections["pre-joint"]["points"] != [centers[0], centers[1]]
            or thigh_sections["joint"]["points"] != [centers[1], centers[2]]
            or shin_sections["pre-joint"]["points"] != [centers[2], centers[3]]
            or shin_sections["joint"]["points"] != [centers[3], centers[4]]
        ):
            raise SurfacePreviewPublishError(f"{where} consumer sections do not bind the exact five-station route")
        thigh_joints = [item for item in thigh["joints"] if item.get("name") == "knee"]
        shin_joints = [item for item in shin["joints"] if item.get("name") == "hock"]
        if len(thigh_joints) != 1 or len(shin_joints) != 1 or thigh_joints[0]["mass"]["center"] != centers[2] or shin_joints[0]["mass"]["center"] != centers[4]:
            raise SurfacePreviewPublishError(f"{where} seam or endpoint centers are not exact")
        if thigh_joints[0]["owner"] != thigh["owner"] or shin_joints[0]["owner"] != shin["owner"]:
            raise SurfacePreviewPublishError(f"{where} knee/hock ownership is not thigh/shin")
        if thigh_joints[0].get("mass", {}).get("control") != "knee" or shin_joints[0].get("mass", {}).get("control") != "hock":
            raise SurfacePreviewPublishError(f"{where} knee/hock mass controls are invalid")
        for joint, station_index, joint_name in (
            (thigh_joints[0], 2, "knee"),
            (shin_joints[0], 4, "hock"),
        ):
            expected_radii = [
                float(guide_sections[station_index]["radii"][axis])
                for axis in AUTHORED_LEG_PROFILE_RADIUS_AXES
            ]
            actual_radii = _point(
                joint["mass"]["radii"],
                f"{where}.{joint_name}.mass.radii",
            )
            if any(
                not math.isclose(actual, expected, rel_tol=0.0, abs_tol=1.0e-12)
                for actual, expected in zip(actual_radii, expected_radii)
            ):
                raise SurfacePreviewPublishError(
                    f"{where} {joint_name} mass radii do not bind the exact leg station"
                )
        if [item.get("control") for item in thigh.get("bridges", [])] != ["root", "hip"] or len(thigh.get("bridges", [])) != 2 or shin.get("bridges") != []:
            raise SurfacePreviewPublishError(f"{where} retained thigh-root/hip bridges or shin bridge inventory is invalid")
        feet = [
            paw for paw in controls["paws"]
            if isinstance(paw, dict)
            and paw.get("owner", {}).get("role") == "foot"
            and paw.get("owner", {}).get("anchors") == [base_side["side"]]
        ]
        if len(feet) != 1 or feet[0].get("hock_source", {}).get("point") != centers[4]:
            raise SurfacePreviewPublishError(f"{where} hock endpoint is not bound by the retained foot source")


def _validate_foot_profile_controls(
    foot_profile: Any,
    controls: dict[str, Any],
    lower: list[float],
    upper: list[float],
    *,
    variant_id: str,
    profile_context: dict[str, Any],
    producer_payload: dict[str, Any],
) -> None:
    """Validate the v10 guide foot route against producer controls and paws."""

    expected_profile_fields = {
        "format", "status", "provenance", "variant_provenance", "axes", "route_topology", "sides"
    }
    if not isinstance(foot_profile, dict) or set(foot_profile) != expected_profile_fields:
        raise SurfacePreviewPublishError("regional guide foot profile controls have an invalid shape")
    if foot_profile["format"] != AUTHORED_FOOT_PROFILE_FORMAT:
        raise SurfacePreviewPublishError("regional guide foot profile format is invalid")
    if foot_profile["status"] != "skin-driving authored foot profile; hock inherited from shin-owned authored leg endpoint":
        raise SurfacePreviewPublishError("regional guide foot profile status is invalid")
    expected_axes = {"lateral": [1.0, 0.0, 0.0], "up": [0.0, 1.0, 0.0], "forward": [0.0, 0.0, 1.0]}
    if foot_profile["axes"] != expected_axes:
        raise SurfacePreviewPublishError("regional guide foot profile axes are invalid")
    if foot_profile["provenance"] != profile_context["provenance"]:
        raise SurfacePreviewPublishError("regional guide foot profile provenance does not bind the producer")
    raw_variant = next((item for item in producer_payload["variants"] if item.get("id") == variant_id), None)
    if not isinstance(raw_variant, dict):
        raise SurfacePreviewPublishError("regional guide foot profile cannot bind its producer variant")
    expected_variant_provenance = raw_variant["foot_profile"]["provenance"]
    if foot_profile["variant_provenance"] != expected_variant_provenance:
        raise SurfacePreviewPublishError("regional guide foot profile variant provenance does not bind the producer variant")
    if foot_profile["route_topology"] != {
        "side_names": list(AUTHORED_FOOT_PROFILE_SIDE_NAMES),
        "section_names": list(AUTHORED_FOOT_PROFILE_SECTION_NAMES),
        "hock_binding": {
            "source_profile": "authored_leg_profile",
            "section_index": AUTHORED_FOOT_PROFILE_HOCK_SECTION_INDEX,
            "owner_role": "shin",
        },
    }:
        raise SurfacePreviewPublishError("regional guide foot profile route topology is invalid")
    sides = foot_profile["sides"]
    if not isinstance(sides, list) or len(sides) != 2 or [item.get("side") for item in sides if isinstance(item, dict)] != list(AUTHORED_FOOT_PROFILE_SIDE_NAMES):
        raise SurfacePreviewPublishError("regional guide foot profile sides are invalid")

    scale = math.sqrt(float(profile_context["reference_scale"]["squared_length"]))
    descriptor_by_owner = {
        _address_sort_key(item["address"]): item
        for item in raw_variant["descriptors"]
        if isinstance(item, dict) and isinstance(item.get("address"), dict)
    }
    leg_sides = controls["leg_profile"]["sides"]
    paws_by_owner = {
        _address_sort_key(item["owner"]): item
        for item in controls["paws"]
        if isinstance(item, dict) and isinstance(item.get("owner"), dict)
    }
    base_sides = profile_context["base_foot_lineage"]
    projected_sides = profile_context["variants"][variant_id]["foot_lineage"]
    section_fields = {
        "name", "section_index", "source_section_index", "frame_index", "landmark_index",
        "owner", "frame", "landmark", "center", "radii", "lateral_radius", "up_radius",
        "forward_radius", "profile_provenance", "variant_provenance", "lineage", "consumption",
    }
    for side_index, (guide_side, base_side, projected_side, leg_side) in enumerate(zip(sides, base_sides, projected_sides, leg_sides)):
        where = f"regional-guide.controls.foot_profile.sides[{side_index}]"
        expected_hock_binding = {
            "source_profile": "authored_leg_profile",
            "side_index": side_index,
            "section_index": AUTHORED_FOOT_PROFILE_HOCK_SECTION_INDEX,
        }
        if not isinstance(guide_side, dict) or set(guide_side) != {"side", "hock_binding", "sections"}:
            raise SurfacePreviewPublishError(f"{where} has an invalid shape")
        if guide_side["side"] != base_side["side"] or guide_side["hock_binding"] != expected_hock_binding or guide_side["hock_binding"] != base_side["hock_binding"]:
            raise SurfacePreviewPublishError(f"{where} does not retain the exact authored hock binding")
        guide_sections = guide_side["sections"]
        if not isinstance(guide_sections, list) or len(guide_sections) != 2:
            raise SurfacePreviewPublishError(f"{where}.sections must contain pad then toe")
        foot_owner = base_side["sections"][0]["owner"]
        descriptor = descriptor_by_owner.get(_address_sort_key(foot_owner))
        if not isinstance(descriptor, dict):
            raise SurfacePreviewPublishError(f"{where} has no matching producer foot descriptor")
        dimension_roles = descriptor.get("dimension_roles")
        if not isinstance(dimension_roles, list):
            raise SurfacePreviewPublishError(f"{where} producer foot descriptor dimensions are invalid")
        paw = paws_by_owner.get(_address_sort_key(foot_owner))
        if not isinstance(paw, dict) or paw.get("owner", {}).get("role") != "foot":
            raise SurfacePreviewPublishError(f"{where} has no matching foot paw chain")
        chain = paw.get("chain")
        if not isinstance(chain, dict):
            raise SurfacePreviewPublishError(f"{where} paw chain is missing")
        hock = chain["hock"]
        leg_hock = leg_side["sections"][AUTHORED_FOOT_PROFILE_HOCK_SECTION_INDEX]
        if hock["center"] != leg_hock["center"] or hock["radii"] != [leg_hock["radii"][axis] for axis in AUTHORED_FOOT_PROFILE_RADIUS_AXES] or leg_hock["owner"]["role"] != "shin":
            raise SurfacePreviewPublishError(f"{where} hock is not the same-side shin-owned leg endpoint")
        if paw["hock_source"]["owner"]["role"] != "shin" or paw["hock_source"]["owner"]["anchors"] != [base_side["side"]] or paw["hock_source"]["point"] != hock["center"]:
            raise SurfacePreviewPublishError(f"{where} hock source is not bound to the same-side shin")
        masses = {item["control"]: item for item in chain["masses"]}
        if chain.get("authored_profile") != guide_side:
            raise SurfacePreviewPublishError(f"{where} paw authored profile is not the exact guide foot side")
        if chain["axes"] != expected_axes:
            raise SurfacePreviewPublishError(f"{where} paw axes do not bind the foot profile axes")
        if not math.isclose(float(masses["paw-pad"]["center"][1]) - float(masses["paw-pad"]["radii"][1]), float(chain["contact_height"]), rel_tol=0.0, abs_tol=1.0e-12) or not math.isclose(float(masses["toe-box"]["center"][1]) - float(masses["toe-box"]["radii"][1]), float(chain["contact_height"]), rel_tol=0.0, abs_tol=1.0e-12):
            raise SurfacePreviewPublishError(f"{where} pad/toe contact does not bind the chain datum")
        expected_centers = (masses["paw-pad"]["center"], masses["toe-box"]["center"])
        expected_radii = (masses["paw-pad"]["radii"], masses["toe-box"]["radii"])
        for section_index, (section, base, projected) in enumerate(zip(guide_sections, base_side["sections"], projected_side["sections"])):
            section_where = f"{where}.sections[{section_index}]"
            if not isinstance(section, dict) or set(section) != section_fields:
                raise SurfacePreviewPublishError(f"{section_where} has an invalid shape")
            if (
                section["name"] != base["name"]
                or section["section_index"] != section_index
                or section["source_section_index"] != section_index
                or section["frame_index"] != base["frame_index"]
                or section["landmark_index"] != base["landmark_index"]
                or section["owner"] != base["owner"]
                or section["frame"] != base["frame"]
                or section["profile_provenance"] != profile_context["provenance"]
                or section["variant_provenance"] != foot_profile["variant_provenance"]
                or section["consumption"] != "skin-driving; pad/toe stations are exact authored foot controls"
            ):
                raise SurfacePreviewPublishError(f"{section_where} identity does not match the producer foot profile")
            expected_landmark = profile_context["landmarks"][_address_sort_key(base["owner"]), base["landmark"]["role"]]
            if section["landmark"] != expected_landmark:
                raise SurfacePreviewPublishError(f"{section_where}.landmark does not match the producer foot profile")
            expected_center = [
                (float(descriptor["reference_point"][axis]) + float(base["landmark"]["position"][axis])) / scale
                for axis in range(3)
            ]
            if section["center"] != expected_center or section["center"] != expected_centers[section_index]:
                raise SurfacePreviewPublishError(f"{section_where}.center is not the exact producer/paw center")
            expected_values = projected["scaled_values_permille"]
            expected_radii_dict = {axis: expected_values[axis] / 1000.0 for axis in AUTHORED_FOOT_PROFILE_RADIUS_AXES}
            if section["radii"] != expected_radii_dict or section["radii"] != dict(zip(AUTHORED_FOOT_PROFILE_RADIUS_AXES, expected_radii[section_index])):
                raise SurfacePreviewPublishError(f"{section_where}.radii do not bind all three authored foot radii")
            if any(section[f"{axis}_radius"] != expected_radii_dict[axis] for axis in AUTHORED_FOOT_PROFILE_RADIUS_AXES):
                raise SurfacePreviewPublishError(f"{section_where} scalar radii are not exact")
            expected_lineage = {
                axis: {
                    "base": dimension["base_value_permille"],
                    "factor": projected["scaling"][axis],
                    "scaled": expected_values[axis],
                    "reference": {"owner": base["owner"], "role": dimension["role"], "index": dimension["index"]},
                    "provenance": profile_context["provenance"],
                    "consumed_section": base["name"],
                }
                for axis, dimension in zip(AUTHORED_FOOT_PROFILE_RADIUS_AXES, base["dimensions"])
            }
            if any(str(dimension["role"]).startswith("form_extent_") for dimension in base["dimensions"]):
                raise SurfacePreviewPublishError(f"{section_where} depends on a legacy foot descriptor extent")
            if section["lineage"] != expected_lineage:
                raise SurfacePreviewPublishError(f"{section_where}.lineage does not bind each producer foot dimension")
            if any(float(value) <= 0.0 for value in section["radii"].values()):
                raise SurfacePreviewPublishError(f"{section_where}.radii must be positive")
            _contained(section["center"], [max(section["radii"].values())] * 3, lower, upper, f"{section_where}.center")


def _validate_controls(
    controls: Any,
    owners: list[dict[str, Any]],
    lower: list[float],
    upper: list[float],
    *,
    variant_id: str,
    producer_payload: dict[str, Any],
) -> None:
    profile_context = _validate_authored_torso_profile(producer_payload)
    torso_profile = profile_context["variants"][variant_id]
    if not isinstance(controls, dict) or set(controls) != {"axes", "axial", "torso_cage", "shoulder_frame", "arm_profile", "leg_profile", "foot_profile", "head", "limbs", "paws", "tails"}:
        raise SurfacePreviewPublishError("regional guide controls are invalid")
    axes = controls["axes"]
    if not isinstance(axes, dict) or set(axes) != {"lateral", "up", "forward"} or axes != {"lateral": [1.0, 0.0, 0.0], "up": [0.0, 1.0, 0.0], "forward": [0.0, 0.0, 1.0]}:
        raise SurfacePreviewPublishError("regional guide axes are invalid")
    owner_keys = {json.dumps(item, sort_keys=True) for item in owners}

    def owner(value: Any, where: str) -> dict[str, Any]:
        parsed = _validate_address(value, where)
        if json.dumps(parsed, sort_keys=True) not in owner_keys:
            raise SurfacePreviewPublishError(f"{where} is not a source owner")
        return parsed

    def close_point(actual: list[float], expected: list[float], where: str) -> None:
        if len(actual) != 3 or len(expected) != 3 or any(
            not math.isclose(float(a), float(b), rel_tol=1.0e-9, abs_tol=1.0e-12)
            for a, b in zip(actual, expected)
        ):
            raise SurfacePreviewPublishError(f"{where} does not bind its expected point")

    axial = controls["axial"]
    if not isinstance(axial, dict) or set(axial) != {"status", "core", "stations", "transitions"} or axial["status"] != "compatibility-diagnostic-not-rendered":
        raise SurfacePreviewPublishError("regional guide axial controls are invalid")
    core = axial["core"]
    if not isinstance(core, dict) or set(core) != {"owner", "recipe", "mass"} or core["recipe"] != "pelvic-core":
        raise SurfacePreviewPublishError("regional guide pelvic core control is invalid")
    core_owner = owner(core["owner"], "regional-guide.controls.axial.core.owner")
    if core_owner["role"] != "pelvis":
        raise SurfacePreviewPublishError("regional guide pelvic core owner role is invalid")
    if _mass(core["mass"], "regional-guide.controls.axial.core.mass", lower, upper, {"pelvic-core"}) != "pelvic-core":
        raise SurfacePreviewPublishError("regional guide pelvic core mass is invalid")

    stations = axial["stations"]
    expected_stations = (
        ("pelvic-girdle", "pelvis", "hips"),
        ("waist", "torso", "waist"),
        ("chest-girdle", "torso", "chest"),
    )
    if not isinstance(stations, list) or len(stations) != len(expected_stations):
        raise SurfacePreviewPublishError("regional guide axial stations are invalid")
    station_y: list[float] = []
    for index, (item, (expected_name, expected_role, expected_recipe)) in enumerate(zip(stations, expected_stations)):
        if not isinstance(item, dict) or set(item) != {"name", "owner", "recipe", "mass"}:
            raise SurfacePreviewPublishError(f"regional guide axial.stations[{index}] has an invalid shape")
        if item["name"] != expected_name or item["recipe"] != expected_recipe:
            raise SurfacePreviewPublishError(f"regional guide axial.stations[{index}] name or recipe is invalid")
        station_owner = owner(item["owner"], f"regional-guide.controls.axial.stations[{index}].owner")
        if station_owner["role"] != expected_role:
            raise SurfacePreviewPublishError(f"regional guide axial.stations[{index}] owner role is invalid")
        _mass(item["mass"], f"regional-guide.controls.axial.stations[{index}].mass", lower, upper, {expected_name})
        station_y.append(_finite_number(item["mass"]["center"][1], f"regional-guide.controls.axial.stations[{index}].mass.center[1]"))
    if not station_y[0] < station_y[1] < station_y[2]:
        raise SurfacePreviewPublishError("regional guide axial stations are not ordered from pelvis to chest")

    transitions = axial["transitions"]
    expected_transitions = (
        ("pelvis-waist", "pelvis-waist-bridge"),
        ("waist-chest", "waist-chest-bridge"),
    )
    if not isinstance(transitions, list) or len(transitions) != len(expected_transitions):
        raise SurfacePreviewPublishError("regional guide axial transitions are invalid")
    for index, (item, (expected_name, expected_recipe)) in enumerate(zip(transitions, expected_transitions)):
        if not isinstance(item, dict) or set(item) != {"name", "owner", "recipe", "path"}:
            raise SurfacePreviewPublishError(f"regional guide axial.transitions[{index}] has an invalid shape")
        if item["name"] != expected_name or item["recipe"] != expected_recipe:
            raise SurfacePreviewPublishError(f"regional guide axial.transitions[{index}] name or recipe is invalid")
        transition_owner = owner(item["owner"], f"regional-guide.controls.axial.transitions[{index}].owner")
        if transition_owner["role"] != "torso":
            raise SurfacePreviewPublishError(f"regional guide axial.transitions[{index}] owner role is invalid")
        _path(item["path"], f"regional-guide.controls.axial.transitions[{index}].path", lower, upper, {expected_name}, expected_kind="tapered-segment")

    torso_cage = controls["torso_cage"]
    expected_cage_fields = {"status", "profile_format", "owners", "axes", "orientation", "sections", "connections"}
    if not isinstance(torso_cage, dict) or set(torso_cage) != expected_cage_fields:
        raise SurfacePreviewPublishError("regional guide torso cage controls are invalid")
    if torso_cage["status"] != "skin-driving torso controls" or torso_cage["profile_format"] != AUTHORED_TORSO_PROFILE_FORMAT:
        raise SurfacePreviewPublishError("regional guide torso cage status is invalid")
    cage_owners = torso_cage["owners"]
    if not isinstance(cage_owners, list) or len(cage_owners) != 2:
        raise SurfacePreviewPublishError("regional guide torso cage owners are invalid")
    parsed_cage_owners = [owner(value, f"regional-guide.controls.torso_cage.owners[{index}]") for index, value in enumerate(cage_owners)]
    if [value["role"] for value in parsed_cage_owners] != ["pelvis", "torso"]:
        raise SurfacePreviewPublishError("regional guide torso cage owners must be pelvis and torso")
    cage_axes = torso_cage["axes"]
    expected_axes = {"lateral": [1.0, 0.0, 0.0], "up": [0.0, 1.0, 0.0], "forward": [0.0, 0.0, 1.0]}
    if cage_axes != expected_axes or torso_cage["orientation"] != "elliptical cross-section rings lie in the lateral/forward plane and rise along the up axis":
        raise SurfacePreviewPublishError("regional guide torso cage axes or orientation is invalid")
    expected_sections = (
        ("lower-pelvis", "pelvis"),
        ("upper-pelvis", "pelvis"),
        ("lower-abdomen", "torso"),
        ("waist-abdomen", "torso"),
        ("upper-abdomen", "torso"),
        ("lower-ribcage", "torso"),
        ("upper-ribcage-shoulder", "torso"),
    )
    sections = torso_cage["sections"]
    if not isinstance(sections, list) or len(sections) != len(expected_sections):
        raise SurfacePreviewPublishError("regional guide torso cage sections are invalid")
    descriptor_by_owner = {}
    raw_variant = next(item for item in producer_payload["variants"] if item.get("id") == variant_id)
    for descriptor in raw_variant["descriptors"]:
        descriptor_by_owner[_address_sort_key(descriptor["address"])] = descriptor
    scale = math.sqrt(float(profile_context["reference_scale"]["squared_length"]))
    section_y: list[float] = []
    for index, (item, (expected_name, expected_role)) in enumerate(zip(sections, expected_sections)):
        expected_section_fields = {"name", "section_index", "frame_index", "landmark_index", "owner", "frame", "landmark", "center", "lateral_radius", "anterior_radius", "posterior_radius", "depth_radius", "lateral", "anterior", "posterior", "lineage"}
        if not isinstance(item, dict) or set(item) != expected_section_fields:
            raise SurfacePreviewPublishError(f"regional guide torso cage sections[{index}] has an invalid shape")
        if item["name"] != expected_name:
            raise SurfacePreviewPublishError(f"regional guide torso cage sections[{index}] name is invalid")
        section_owner = owner(item["owner"], f"regional-guide.controls.torso_cage.sections[{index}].owner")
        if section_owner["role"] != expected_role or section_owner != parsed_cage_owners[0 if expected_role == "pelvis" else 1]:
            raise SurfacePreviewPublishError(f"regional guide torso cage sections[{index}] owner is invalid")
        base = torso_profile["torso_lineage"][index]
        if (
            type(item["section_index"]) is not int
            or item["section_index"] != index
            or type(item["frame_index"]) is not int
            or item["frame_index"] != base["frame_index"]
            or type(item["landmark_index"]) is not int
            or item["landmark_index"] != base["landmark_index"]
        ):
            raise SurfacePreviewPublishError(f"regional guide torso cage sections[{index}] indexed identity references do not match authored profile")
        expected_frame = base["frame"]
        expected_landmark_key = (_address_sort_key(base["owner"]), base["landmark"]["role"])
        expected_landmark = profile_context["landmarks"][expected_landmark_key]
        if item["frame"] != expected_frame or item["landmark"] != expected_landmark:
            raise SurfacePreviewPublishError(f"regional guide torso cage sections[{index}] source frame or landmark does not match authored profile")
        descriptor = descriptor_by_owner.get(_address_sort_key(base["owner"]))
        if not isinstance(descriptor, dict) or not isinstance(descriptor.get("reference_point"), list):
            raise SurfacePreviewPublishError(f"regional guide torso cage sections[{index}] cannot bind the source reference point")
        expected_center = [
            (float(descriptor["reference_point"][axis]) + float(base["landmark"]["position"][axis])) / scale
            for axis in range(3)
        ]
        center = _point(item["center"], f"regional-guide.controls.torso_cage.sections[{index}].center")
        if any(not math.isclose(actual, expected, rel_tol=0.0, abs_tol=1.0e-12) for actual, expected in zip(center, expected_center)):
            raise SurfacePreviewPublishError(f"regional guide torso cage sections[{index}].center does not match authored profile")
        expected_values = base["scaled_values_permille"]
        radii = [
            _finite_number(item[f"{axis}_radius"], f"regional-guide.controls.torso_cage.sections[{index}].{axis}_radius")
            for axis in AUTHORED_TORSO_PROFILE_RADIUS_AXES
        ]
        expected_radii = [expected_values[axis] / 1000.0 for axis in AUTHORED_TORSO_PROFILE_RADIUS_AXES]
        if any(not math.isclose(actual, expected, rel_tol=0.0, abs_tol=1.0e-12) for actual, expected in zip(radii, expected_radii)):
            raise SurfacePreviewPublishError(f"regional guide torso cage sections[{index}] radii do not match authored profile")
        depth = _finite_number(item["depth_radius"], f"regional-guide.controls.torso_cage.sections[{index}].depth_radius")
        if not math.isclose(depth, sum(expected_radii[1:]) / 2.0, rel_tol=0.0, abs_tol=1.0e-12):
            raise SurfacePreviewPublishError(f"regional guide torso cage sections[{index}].depth_radius does not match authored profile")
        if any(value <= 0.0 for value in radii) or depth <= 0.0:
            raise SurfacePreviewPublishError(f"regional guide torso cage sections[{index}] radii must be positive")
        if center[0] - radii[0] < lower[0] or center[0] + radii[0] > upper[0] or center[2] - depth < lower[2] or center[2] + depth > upper[2] or center[1] < lower[1] or center[1] > upper[1]:
            raise SurfacePreviewPublishError(f"regional guide torso cage sections[{index}] extend outside shared render bounds")
        expected_lineage = {}
        for axis, dimension in zip(AUTHORED_TORSO_PROFILE_RADIUS_AXES, base["dimensions"]):
            factor = base["scaling"][axis]
            expected_lineage[axis] = {
                "base": dimension["base_value_permille"],
                "factor": factor,
                "scaled": expected_values[axis],
                "reference": {"owner": base["owner"], "role": dimension["role"], "index": dimension["index"]},
                "provenance": profile_context["provenance"],
                "consumed_section": expected_name,
            }
        if any(item.get(axis) != expected_lineage[axis] for axis in AUTHORED_TORSO_PROFILE_RADIUS_AXES) or item.get("lineage") != expected_lineage:
            raise SurfacePreviewPublishError(f"regional guide torso cage sections[{index}] radius lineage does not match authored profile")
        section_y.append(center[1])
    if any(section_y[index] >= section_y[index + 1] for index in range(len(section_y) - 1)):
        raise SurfacePreviewPublishError("regional guide torso cage sections are not ordered from pelvis to shoulders")
    connections = torso_cage["connections"]
    expected_connections = [{"from": expected_sections[index][0], "to": expected_sections[index + 1][0]} for index in range(len(expected_sections) - 1)]
    if connections != expected_connections:
        raise SurfacePreviewPublishError("regional guide torso cage connections are invalid")

    shoulder = controls["shoulder_frame"]
    if not isinstance(shoulder, dict) or set(shoulder) != {"status", "owners", "central", "source_controls", "sides"} or shoulder["status"] != "private shoulder frame; support curves guide-only; deltoid sweep skin-driving":
        raise SurfacePreviewPublishError("regional guide shoulder frame controls are invalid")
    shoulder_owners = shoulder["owners"]
    if not isinstance(shoulder_owners, dict) or set(shoulder_owners) != {"torso", "neck", "left_upper_arm", "right_upper_arm"}:
        raise SurfacePreviewPublishError("regional guide shoulder frame owners are invalid")
    parsed_shoulder_owners = {key: owner(value, f"regional-guide.controls.shoulder_frame.owners.{key}") for key, value in shoulder_owners.items()}
    if parsed_shoulder_owners["torso"]["role"] != "torso" or parsed_shoulder_owners["neck"]["role"] != "neck":
        raise SurfacePreviewPublishError("regional guide shoulder frame central owners are invalid")
    if parsed_shoulder_owners["left_upper_arm"]["role"] != "upper_arm" or parsed_shoulder_owners["left_upper_arm"]["anchors"] != ["left"]:
        raise SurfacePreviewPublishError("regional guide shoulder frame left owner is invalid")
    if parsed_shoulder_owners["right_upper_arm"]["role"] != "upper_arm" or parsed_shoulder_owners["right_upper_arm"]["anchors"] != ["right"]:
        raise SurfacePreviewPublishError("regional guide shoulder frame right owner is invalid")

    central = shoulder["central"]
    if not isinstance(central, dict) or set(central) != {"owner", "anchor", "profile"}:
        raise SurfacePreviewPublishError("regional guide shoulder frame central control is invalid")
    if owner(central["owner"], "regional-guide.controls.shoulder_frame.central.owner") != parsed_shoulder_owners["torso"]:
        raise SurfacePreviewPublishError("regional guide shoulder frame central owner is invalid")
    _point(central["anchor"], "regional-guide.controls.shoulder_frame.central.anchor")
    profile = central["profile"]
    if not isinstance(profile, list) or len(profile) != 2 or any(_finite_number(value, "regional-guide.controls.shoulder_frame.central.profile") <= 0.0 for value in profile):
        raise SurfacePreviewPublishError("regional guide shoulder frame central profile is invalid")
    producer_source = producer_payload.get("source")
    producer_scale = producer_payload.get("reference_scale")
    producer_frames = producer_payload.get("authored_frames")
    producer_landmarks = producer_payload.get("authored_landmarks")
    producer_dimensions = producer_payload.get("authored_dimensions")
    producer_variants = producer_payload.get("variants")
    if (
        not isinstance(producer_source, dict)
        or not isinstance(producer_scale, dict)
        or not isinstance(producer_frames, list)
        or not isinstance(producer_landmarks, list)
        or not isinstance(producer_dimensions, list)
        or not isinstance(producer_variants, list)
    ):
        raise SurfacePreviewPublishError("regional guide cannot bind v10 producer shoulder controls")
    squared_length = producer_scale.get("squared_length")
    if type(squared_length) is not int or squared_length <= 0:
        raise SurfacePreviewPublishError("regional guide cannot bind the producer reference scale")
    reference_scale = math.sqrt(float(squared_length))
    producer_variant = next(
        (
            item
            for item in producer_variants
            if isinstance(item, dict) and item.get("id") == variant_id
        ),
        None,
    )
    if not isinstance(producer_variant, dict) or not isinstance(producer_variant.get("descriptors"), list):
        raise SurfacePreviewPublishError("regional guide cannot bind its producer variant")

    source_controls = shoulder["source_controls"]
    if not isinstance(source_controls, list) or len(source_controls) != 2:
        raise SurfacePreviewPublishError("regional guide shoulder source controls are invalid")
    expected_factor = {
        "neutral-v0": 1_000,
        "broad-soft-v0": 1_150,
        "lean-readable-v0": 800,
        "depth-forward-v0": 1_000,
    }.get(variant_id)
    if expected_factor is None:
        raise SurfacePreviewPublishError("regional guide shoulder source-control variant is invalid")

    source_controls_by_side: dict[str, dict[str, Any]] = {}
    expected_control_records: dict[str, dict[str, Any]] = {}
    for control_index, control in enumerate(source_controls):
        control_where = f"regional-guide.controls.shoulder_frame.source_controls[{control_index}]"
        if not isinstance(control, dict) or set(control) != {"side", "owner", "frame", "landmarks", "depth_control"}:
            raise SurfacePreviewPublishError(f"{control_where} has an invalid shape")
        side_name = control.get("side")
        if side_name not in {"left", "right"} or side_name in source_controls_by_side:
            raise SurfacePreviewPublishError(f"{control_where}.side is invalid or duplicated")
        expected_owner = parsed_shoulder_owners[f"{side_name}_upper_arm"]
        if owner(control.get("owner"), f"{control_where}.owner") != expected_owner:
            raise SurfacePreviewPublishError(f"{control_where}.owner is invalid")
        expected_frames = [
            item
            for item in producer_frames
            if isinstance(item, dict)
            and item.get("owner") == expected_owner
            and item.get("role") == "form_shoulder_control"
        ]
        if len(expected_frames) != 1 or control.get("frame") != expected_frames[0]:
            raise SurfacePreviewPublishError(f"{control_where}.frame does not match the producer")
        expected_landmarks = [
            item
            for item in producer_landmarks
            if isinstance(item, dict)
            and item.get("owner") == expected_owner
            and item.get("role") in {"form_axilla", "form_shoulder_peak"}
        ]
        if len(expected_landmarks) != 2 or control.get("landmarks") != expected_landmarks:
            raise SurfacePreviewPublishError(f"{control_where}.landmarks do not match the producer")
        expected_dimensions = [
            item
            for item in producer_dimensions
            if isinstance(item, dict)
            and item.get("owner") == expected_owner
            and item.get("role") == "form_shoulder_depth_radius"
        ]
        depth_control = control.get("depth_control")
        if len(expected_dimensions) != 1 or not isinstance(depth_control, dict):
            raise SurfacePreviewPublishError(f"{control_where}.depth_control cannot bind the producer")
        if set(depth_control) != {
            "owner", "role", "value_permille", "scaled_value_permille",
            "profile_factor", "provenance", "consumption",
        }:
            raise SurfacePreviewPublishError(f"{control_where}.depth_control has an invalid shape")
        expected_dimension = expected_dimensions[0]
        raw_value = expected_dimension.get("value_permille")
        if type(raw_value) is not int or raw_value <= 0:
            raise SurfacePreviewPublishError(f"{control_where}.depth_control producer value is invalid")
        expected_scaled = raw_value * expected_factor // 1_000
        if (
            depth_control.get("owner") != expected_dimension.get("owner")
            or depth_control.get("role") != expected_dimension.get("role")
            or depth_control.get("value_permille") != raw_value
            or depth_control.get("scaled_value_permille") != expected_scaled
            or depth_control.get("profile_factor") != expected_factor
            or depth_control.get("provenance") != expected_dimension.get("provenance")
            or depth_control.get("consumption")
            != "guide-derived shoulder wrap depth; baseline field remains guide-only"
        ):
            raise SurfacePreviewPublishError(f"{control_where}.depth_control does not match the producer and variant")
        descriptors = [
            item
            for item in producer_variant["descriptors"]
            if isinstance(item, dict) and item.get("address") == expected_owner
        ]
        if len(descriptors) != 1:
            raise SurfacePreviewPublishError(f"{control_where} has no unique producer descriptor")
        reference_point = descriptors[0].get("reference_point")
        if not isinstance(reference_point, list) or len(reference_point) != 3:
            raise SurfacePreviewPublishError(f"{control_where} producer reference point is invalid")
        landmark_by_role = {item["role"]: item for item in expected_landmarks}
        derived: dict[str, list[float]] = {}
        for role in ("form_axilla", "form_shoulder_peak"):
            position = landmark_by_role[role].get("position")
            if not isinstance(position, list) or len(position) != 3:
                raise SurfacePreviewPublishError(f"{control_where}.{role} position is invalid")
            derived[role] = [
                (float(reference_point[axis]) + float(position[axis])) / reference_scale
                for axis in range(3)
            ]
        source_controls_by_side[side_name] = control
        expected_control_records[side_name] = {
            "frame": expected_frames[0],
            "axilla": landmark_by_role["form_axilla"],
            "peak": landmark_by_role["form_shoulder_peak"],
            "axilla_anchor": derived["form_axilla"],
            "peak_anchor": derived["form_shoulder_peak"],
            "depth_control": depth_control,
            "depth_radius": expected_scaled / 1_000.0,
        }
    if list(source_controls_by_side) != ["left", "right"]:
        raise SurfacePreviewPublishError("regional guide shoulder source controls are not in canonical side order")

    sides = shoulder["sides"]
    if not isinstance(sides, list) or len(sides) != 2 or [item.get("side") for item in sides if isinstance(item, dict)] != ["left", "right"]:
        raise SurfacePreviewPublishError("regional guide shoulder frame sides are invalid")
    for index, side in enumerate(sides):
        where = f"regional-guide.controls.shoulder_frame.sides[{index}]"
        if not isinstance(side, dict) or set(side) != {
            "side", "owner", "socket", "extremum", "authored_controls",
            "peak_anchor", "axilla_anchor", "vertical_midpoint", "vertical_radius",
            "depth_radius", "depth_control", "span", "slope", "curves",
        }:
            raise SurfacePreviewPublishError(f"{where} has an invalid shape")
        side_owner = owner(side["owner"], f"{where}.owner")
        expected_owner = parsed_shoulder_owners[f"{side['side']}_upper_arm"]
        if side_owner != expected_owner:
            raise SurfacePreviewPublishError(f"{where}.owner is invalid")
        expected_records = expected_control_records[side["side"]]
        authored_controls = side["authored_controls"]
        if not isinstance(authored_controls, dict) or set(authored_controls) != {"peak", "axilla", "frame"}:
            raise SurfacePreviewPublishError(f"{where}.authored_controls are invalid")
        if (
            authored_controls["peak"] != expected_records["peak"]
            or authored_controls["axilla"] != expected_records["axilla"]
            or authored_controls["frame"] != expected_records["frame"]
            or side["depth_control"] != expected_records["depth_control"]
        ):
            raise SurfacePreviewPublishError(f"{where}.authored_controls do not match the producer")
        peak_anchor = _point(side["peak_anchor"], f"{where}.peak_anchor")
        axilla_anchor = _point(side["axilla_anchor"], f"{where}.axilla_anchor")
        close_point(peak_anchor, expected_records["peak_anchor"], f"{where}.peak_anchor")
        close_point(axilla_anchor, expected_records["axilla_anchor"], f"{where}.axilla_anchor")
        expected_midpoint = 0.5 * (peak_anchor[1] + axilla_anchor[1])
        expected_vertical_radius = 0.5 * (peak_anchor[1] - axilla_anchor[1])
        if (
            expected_vertical_radius <= 0.0
            or not math.isclose(_finite_number(side["vertical_midpoint"], f"{where}.vertical_midpoint"), expected_midpoint, rel_tol=0.0, abs_tol=1.0e-12)
            or not math.isclose(_finite_number(side["vertical_radius"], f"{where}.vertical_radius"), expected_vertical_radius, rel_tol=0.0, abs_tol=1.0e-12)
            or not math.isclose(_finite_number(side["depth_radius"], f"{where}.depth_radius"), float(expected_records["depth_radius"]), rel_tol=0.0, abs_tol=1.0e-12)
        ):
            raise SurfacePreviewPublishError(f"{where} derived authored shoulder controls are invalid")
        for control_name in ("socket", "extremum"):
            control = side[control_name]
            if not isinstance(control, dict) or set(control) != {"owner", "point"} or owner(control["owner"], f"{where}.{control_name}.owner") != side_owner:
                raise SurfacePreviewPublishError(f"{where}.{control_name} is invalid")
            _point(control["point"], f"{where}.{control_name}.point")
        close_point(side["extremum"]["point"], peak_anchor, f"{where}.extremum")
        span = _finite_number(side["span"], f"{where}.span")
        if span <= 0.0 or not math.isfinite(_finite_number(side["slope"], f"{where}.slope")):
            raise SurfacePreviewPublishError(f"{where}.span or slope is invalid")
        curves = side["curves"]
        if not isinstance(curves, list) or [item.get("name") for item in curves if isinstance(item, dict)] != ["anterior-support", "posterior-return", "deltoid-sweep"]:
            raise SurfacePreviewPublishError(f"{where}.curves are invalid")
        for curve_index, curve in enumerate(curves):
            curve_where = f"{where}.curves[{curve_index}]"
            if not isinstance(curve, dict) or set(curve) != {"name", "owner", "points", "profile", "consumption"}:
                raise SurfacePreviewPublishError(f"{curve_where} has an invalid shape")
            expected_curve_owner = parsed_shoulder_owners["torso"] if curve["name"] != "deltoid-sweep" else side_owner
            if owner(curve["owner"], f"{curve_where}.owner") != expected_curve_owner:
                raise SurfacePreviewPublishError(f"{curve_where}.owner is invalid")
            expected_consumption = "skin-driving" if curve["name"] == "deltoid-sweep" else "guide-only"
            if curve["consumption"] != expected_consumption:
                raise SurfacePreviewPublishError(f"{curve_where}.consumption is invalid")
            points = curve["points"]
            expected_point_count = 3 if curve["name"] == "deltoid-sweep" else 4
            if not isinstance(points, list) or len(points) != expected_point_count:
                raise SurfacePreviewPublishError(f"{curve_where}.points are invalid")
            for point_index, point in enumerate(points):
                _point(point, f"{curve_where}.points[{point_index}]")
            curve_profile = curve["profile"]
            if not isinstance(curve_profile, list) or len(curve_profile) != expected_point_count or any(_finite_number(value, f"{curve_where}.profile") <= 0.0 for value in curve_profile):
                raise SurfacePreviewPublishError(f"{curve_where}.profile is invalid")
            parsed_profile = [_finite_number(value, f"{curve_where}.profile[{profile_index}]") for profile_index, value in enumerate(curve_profile)]
            for point_index, point in enumerate(points):
                parsed_point = _point(point, f"{curve_where}.points[{point_index}]")
                radius = parsed_profile[point_index]
                if any(parsed_point[axis] - radius < lower[axis] or parsed_point[axis] + radius > upper[axis] for axis in range(3)):
                    raise SurfacePreviewPublishError(f"{curve_where}.point[{point_index}] extends outside shared render bounds")

    _validate_arm_profile_controls(
        controls["arm_profile"],
        controls,
        lower,
        upper,
        variant_id=variant_id,
        producer_payload=producer_payload,
    )
    _validate_leg_profile_controls(
        controls["leg_profile"],
        controls,
        lower,
        upper,
        variant_id=variant_id,
        producer_payload=producer_payload,
    )

    head = controls["head"]
    if not isinstance(head, dict) or set(head) != {
        "owners", "profile_format", "provenance", "sections", "connections", "masses", "paths"
    }:
        raise SurfacePreviewPublishError("regional guide head controls are invalid")
    head_owners = head["owners"]
    if not isinstance(head_owners, list) or len(head_owners) != 2:
        raise SurfacePreviewPublishError("regional guide head owners are invalid")
    parsed_head_owners = [
        owner(value, f"regional-guide.controls.head.owners[{index}]")
        for index, value in enumerate(head_owners)
    ]
    if (
        [value["role"] for value in parsed_head_owners] != ["head", "neck"]
        or parsed_head_owners[0]["anchors"] != []
        or parsed_head_owners[1]["anchors"] != []
    ):
        raise SurfacePreviewPublishError("regional guide head owners are invalid")
    if (
        head["profile_format"] != AUTHORED_HEAD_NECK_PROFILE_FORMAT
        or head["provenance"] != profile_context["provenance"]
    ):
        raise SurfacePreviewPublishError("regional guide head profile identity is invalid")

    base_head = profile_context["base_head_neck_lineage"]
    variant_head = profile_context["variants"][variant_id]["head_neck_lineage"]
    descriptor_by_owner = {
        _address_sort_key(descriptor["address"]): descriptor
        for descriptor in next(
            item for item in producer_payload["variants"] if item.get("id") == variant_id
        )["descriptors"]
    }
    guide_sections = head["sections"]
    if not isinstance(guide_sections, list) or len(guide_sections) != len(base_head):
        raise SurfacePreviewPublishError(
            "regional guide head profile sections must contain exactly eight records"
        )
    scale = math.sqrt(float(profile_context["reference_scale"]["squared_length"]))
    for index, (section, base, projected) in enumerate(zip(guide_sections, base_head, variant_head)):
        section_where = f"regional-guide.controls.head.sections[{index}]"
        expected_fields = {
            "name", "section_index", "source_section_index", "frame_index", "landmark_index",
            "owner", "frame", "landmark", "center", "radii", "lateral_radius", "up_radius",
            "forward_radius", "lineage",
        }
        if not isinstance(section, dict) or set(section) != expected_fields:
            raise SurfacePreviewPublishError(f"{section_where} has an invalid shape")
        if (
            section["name"] != base["name"]
            or section["section_index"] != index
            or section["source_section_index"] != index
            or section["frame_index"] != base["frame_index"]
            or section["landmark_index"] != base["landmark_index"]
            or section["owner"] != base["owner"]
            or section["frame"] != base["frame"]
        ):
            raise SurfacePreviewPublishError(
                f"{section_where} indexed identity does not match the producer profile"
            )
        expected_landmark = profile_context["landmarks"][
            (_address_sort_key(base["owner"]), base["landmark"]["role"])
        ]
        if section["landmark"] != expected_landmark:
            raise SurfacePreviewPublishError(
                f"{section_where}.landmark does not match the producer profile"
            )
        descriptor = descriptor_by_owner.get(_address_sort_key(base["owner"]))
        if not isinstance(descriptor, dict):
            raise SurfacePreviewPublishError(f"{section_where} has no source descriptor")
        expected_center = [
            (float(descriptor["reference_point"][axis]) + float(base["landmark"]["position"][axis])) / scale
            for axis in range(3)
        ]
        center = _point(section["center"], f"{section_where}.center")
        if any(not math.isclose(actual, expected, rel_tol=0.0, abs_tol=1.0e-12) for actual, expected in zip(center, expected_center)):
            raise SurfacePreviewPublishError(f"{section_where}.center does not bind its source position")
        expected_radii = {
            axis: projected["scaled_values_permille"][axis] / 1000.0
            for axis in AUTHORED_HEAD_NECK_PROFILE_RADIUS_AXES
        }
        if section["radii"] != expected_radii or any(
            not math.isclose(float(section[f"{axis}_radius"]), expected_radii[axis], rel_tol=0.0, abs_tol=1.0e-12)
            for axis in AUTHORED_HEAD_NECK_PROFILE_RADIUS_AXES
        ):
            raise SurfacePreviewPublishError(f"{section_where}.radii do not bind the variant profile")
        expected_lineage = {}
        for axis, dimension in zip(AUTHORED_HEAD_NECK_PROFILE_RADIUS_AXES, base["dimensions"]):
            expected_lineage[axis] = {
                "base": dimension["base_value_permille"],
                "factor": projected["scaling"][axis],
                "scaled": projected["scaled_values_permille"][axis],
                "reference": {
                    "owner": base["owner"],
                    "role": dimension["role"],
                    "index": dimension["index"],
                },
                "provenance": dimension["provenance"] if "provenance" in dimension else profile_context["provenance"],
                "consumed_section": base["name"],
            }
        if section["lineage"] != expected_lineage:
            raise SurfacePreviewPublishError(f"{section_where}.lineage does not bind source dimensions")

    expected_connections = []
    for index, (name, from_index, to_index, route) in enumerate(common.PROVISIONAL_FORM_HEAD_NECK_PROFILE_CONNECTIONS):
        connection_where = f"regional-guide.controls.head.connections[{index}]"
        if not isinstance(head["connections"], list) or index >= len(head["connections"]):
            raise SurfacePreviewPublishError("regional guide head profile connections are incomplete")
        connection = head["connections"][index]
        if not isinstance(connection, dict) or set(connection) != {
            "name", "from_section_index", "to_section_index", "route", "from", "to", "path"
        }:
            raise SurfacePreviewPublishError(f"{connection_where} has an invalid shape")
        source_from = guide_sections[from_index]
        source_to = guide_sections[to_index]
        expected_path = {
            "control": name,
            "points": [source_from["center"], source_to["center"]],
            "thickness": [
                min(float(value) for value in source_from["radii"].values()),
                min(float(value) for value in source_to["radii"].values()),
            ],
            "path_kind": "tapered-segment",
        }
        expected_connection = {
            "name": name,
            "from_section_index": from_index,
            "to_section_index": to_index,
            "route": route,
            "from": {"name": source_from["name"], "owner": source_from["owner"]},
            "to": {"name": source_to["name"], "owner": source_to["owner"]},
            "path": expected_path,
        }
        if connection != expected_connection:
            raise SurfacePreviewPublishError(
                f"{connection_where} does not bind the exact producer connection"
            )
        _path(connection["path"], connection_where + ".path", lower, upper, {name}, expected_kind="tapered-segment")
        expected_connections.append(expected_connection)
    if len(head["connections"]) != len(expected_connections):
        raise SurfacePreviewPublishError("regional guide head profile connections must contain exactly seven records")

    # The complete profile above is source-owned carried guide data.  The
    # compatibility renderer consumes only these three named stations and the
    # two transition paths below; it must not silently claim every profile
    # station as a skin-driving baseline primitive.
    expected_masses = []
    for control, section_name in (
        ("cranium", "cranium-mid"),
        ("muzzle", "muzzle-mid"),
        ("neck-collar", "neck-collar"),
    ):
        selected = next(section for section in guide_sections if section["name"] == section_name)
        expected_masses.append({
            "control": control,
            "center": selected["center"],
            "radii": [selected["radii"][axis] for axis in ("lateral", "up", "forward")],
        })
    if head["masses"] != expected_masses:
        raise SurfacePreviewPublishError("regional guide head compatibility masses do not bind selected profile stations")
    expected_paths = []
    for control, from_name, to_name in (
        ("head-transition", "neck-upper", "head-base"),
        ("neck-transition", "neck-collar", "neck-upper"),
    ):
        source_from = next(section for section in guide_sections if section["name"] == from_name)
        source_to = next(section for section in guide_sections if section["name"] == to_name)
        expected_paths.append({
            "control": control,
            "points": [source_from["center"], source_to["center"]],
            "thickness": [
                min(float(value) for value in source_from["radii"].values()),
                min(float(value) for value in source_to["radii"].values()),
            ],
        })
    if head["paths"] != expected_paths:
        raise SurfacePreviewPublishError("regional guide head compatibility paths do not bind selected profile stations")

    limbs = controls["limbs"]
    if not isinstance(limbs, list) or len(limbs) != 8:
        raise SurfacePreviewPublishError("regional guide limb controls are invalid")
    section_by_role = {
        "upper_arm": {"pre-joint", "joint"},
        "forearm": {"proximal", "distal"},
        "thigh": {"pre-joint", "joint"},
        "shin": {"pre-joint", "joint"},
    }
    section_order_by_role = {
        "upper_arm": ("pre-joint", "joint"),
        "forearm": ("proximal", "distal"),
        "thigh": ("pre-joint", "joint"),
        "shin": ("pre-joint", "joint"),
    }
    bridge_by_role = {"upper_arm": {"root"}, "forearm": set(), "thigh": {"root", "hip"}, "shin": set()}
    masses_by_role = {"upper_arm": {"shoulder-girdle"}, "forearm": set(), "thigh": {"hip-girdle"}, "shin": set()}
    joints_by_role = {"upper_arm": {"elbow"}, "forearm": set(), "thigh": {"knee"}, "shin": {"hock"}}
    limb_owner_keys: set[str] = set()
    limb_roles: list[str] = []
    hock_centers: dict[tuple[str, ...], list[float]] = {}
    hock_records: dict[tuple[str, ...], tuple[dict[str, Any], list[dict[str, Any]]]] = {}
    limb_by_owner_key: dict[str, dict[str, Any]] = {}
    anchor_by_owner_key: dict[str, dict[str, Any]] = {}
    joint_records: list[tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]] = []
    authored_elbows_by_owner = {
        json.dumps(section["owner"], sort_keys=True): section
        for side in controls["arm_profile"]["sides"]
        for section in side["sections"]
        if section["name"] == "elbow"
    }
    for index, item in enumerate(limbs):
        if not isinstance(item, dict) or set(item) != {"owner", "profile_controls", "sections", "bridges", "masses", "joints", "anchors"}:
            raise SurfacePreviewPublishError(f"regional guide limbs[{index}] has an invalid shape")
        parsed_owner = owner(item["owner"], f"regional-guide.controls.limbs[{index}].owner")
        role = parsed_owner["role"]
        if role not in section_by_role:
            raise SurfacePreviewPublishError(f"regional guide limbs[{index}] owner role is invalid")
        owner_key = json.dumps(parsed_owner, sort_keys=True)
        if owner_key in limb_owner_keys:
            raise SurfacePreviewPublishError(f"regional guide limbs[{index}] owner is duplicated")
        limb_owner_keys.add(owner_key)
        limb_by_owner_key[owner_key] = item
        limb_roles.append(role)
        profile_controls = item["profile_controls"]
        if not isinstance(profile_controls, list) or len(profile_controls) != 3 or any(_finite_number(value, f"regional-guide.controls.limbs[{index}].profile_controls") <= 0.0 for value in profile_controls):
            raise SurfacePreviewPublishError(f"regional guide limbs[{index}].profile_controls is invalid")
        sections = item["sections"]
        _path_list(sections, f"regional-guide.controls.limbs[{index}].sections", lower, upper, section_by_role[role], expected_kind="capsule")
        if not isinstance(sections, list) or len(sections) != 2:
            raise SurfacePreviewPublishError(f"regional guide limbs[{index}].sections must contain two pieces")
        by_section = {section["control"]: section for section in sections}
        ordered_sections = [by_section[name] for name in section_order_by_role[role]]
        if float(ordered_sections[0]["thickness"][0]) != float(profile_controls[0]):
            raise SurfacePreviewPublishError(f"regional guide limbs[{index}] profile controls do not bind section geometry")
        # The section break is the middle profile control.  The final distal
        # control is consumed by the second piece; no whole-segment fill is
        # permitted in this private sidecar.
        if (
            float(ordered_sections[0]["thickness"][1]) != float(profile_controls[1])
            or float(ordered_sections[1]["thickness"][0]) != float(profile_controls[1])
            or float(ordered_sections[1]["thickness"][1]) != float(profile_controls[2])
        ):
            raise SurfacePreviewPublishError(f"regional guide limbs[{index}] profile controls do not bind section geometry")
        if ordered_sections[0]["points"][1] != ordered_sections[1]["points"][0]:
            raise SurfacePreviewPublishError(f"regional guide limbs[{index}] sections have a gap or overlap")
        expected_anchor = {
            "forearm": ("forearm-distal-boundary", "parent-surface-anchor"),
            "shin": ("hock-endpoint", "endpoint"),
        }.get(role)
        anchors = item["anchors"]
        if not isinstance(anchors, list) or len(anchors) != (1 if expected_anchor is not None else 0):
            raise SurfacePreviewPublishError(f"regional guide limbs[{index}].anchors are invalid")
        if expected_anchor is not None:
            anchor = anchors[0]
            if not isinstance(anchor, dict) or set(anchor) != {"name", "kind", "point", "boundary_point"}:
                raise SurfacePreviewPublishError(f"regional guide limbs[{index}].anchors[0] has an invalid shape")
            if (anchor["name"], anchor["kind"]) != expected_anchor:
                raise SurfacePreviewPublishError(f"regional guide limbs[{index}].anchors[0] is invalid")
            anchor["point"] = _point(anchor["point"], f"regional-guide.controls.limbs[{index}].anchors[0].point")
            anchor["boundary_point"] = _point(anchor["boundary_point"], f"regional-guide.controls.limbs[{index}].anchors[0].boundary_point")
            if anchor["boundary_point"] != ordered_sections[-1]["points"][1]:
                raise SurfacePreviewPublishError(f"regional guide limbs[{index}].anchors[0] does not bind the distal boundary")
            anchor_by_owner_key[owner_key] = anchor
        _path_list(item["bridges"], f"regional-guide.controls.limbs[{index}].bridges", lower, upper, bridge_by_role[role], expected_kind="tapered-segment")
        _mass_list(item["masses"], f"regional-guide.controls.limbs[{index}].masses", lower, upper, masses_by_role[role])
        joints = item["joints"]
        if not isinstance(joints, list) or len(joints) != len(joints_by_role[role]):
            raise SurfacePreviewPublishError(f"regional guide limbs[{index}].joints are invalid")
        seen_joints: set[str] = set()
        for joint_index, joint in enumerate(joints):
            joint_where = f"regional-guide.controls.limbs[{index}].joints[{joint_index}]"
            if not isinstance(joint, dict) or set(joint) != {"name", "owner", "mass", "adjacent_profiles"}:
                raise SurfacePreviewPublishError(f"{joint_where} has an invalid shape")
            if joint["name"] not in joints_by_role[role] or joint["name"] in seen_joints:
                raise SurfacePreviewPublishError(f"{joint_where}.name is invalid")
            seen_joints.add(joint["name"])
            if owner(joint["owner"], f"{joint_where}.owner") != parsed_owner:
                raise SurfacePreviewPublishError(f"{joint_where}.owner must be the limb source owner")
            if _mass(joint["mass"], f"{joint_where}.mass", lower, upper, {joint["name"]}) != joint["name"]:
                raise SurfacePreviewPublishError(f"{joint_where}.mass is invalid")
            adjacent_profiles = joint["adjacent_profiles"]
            if not isinstance(adjacent_profiles, list) or len(adjacent_profiles) != 2 or any(_finite_number(value, f"{joint_where}.adjacent_profiles") <= 0.0 for value in adjacent_profiles):
                raise SurfacePreviewPublishError(f"{joint_where}.adjacent_profiles is invalid")
            if float(adjacent_profiles[0]) != float(ordered_sections[-1]["thickness"][1]):
                raise SurfacePreviewPublishError(f"{joint_where}.adjacent_profiles do not bind the distal section")
            joint_radii = _point(joint["mass"]["radii"], f"{joint_where}.mass.radii")
            if joint["name"] == "elbow":
                authored_elbow = authored_elbows_by_owner.get(owner_key)
                if authored_elbow is None:
                    raise SurfacePreviewPublishError(
                        f"{joint_where}.mass has no authored elbow station"
                    )
                expected_radii = [
                    float(authored_elbow["radii"][axis])
                    for axis in AUTHORED_ARM_PROFILE_RADIUS_AXES
                ]
                if (
                    joint["mass"]["center"] != authored_elbow["center"]
                    or any(
                        not math.isclose(actual, expected, rel_tol=0.0, abs_tol=1.0e-12)
                        for actual, expected in zip(joint_radii, expected_radii)
                    )
                ):
                    raise SurfacePreviewPublishError(
                        f"{joint_where}.mass does not bind the authored elbow station"
                    )
            elif joint["name"] not in {"knee", "hock"}:
                joint_radius = joint_radii[0]
                if any(not math.isclose(value, joint_radius, rel_tol=1e-9, abs_tol=1e-12) for value in joint_radii[1:]):
                    raise SurfacePreviewPublishError(f"{joint_where}.mass must be isotropic")
                if not math.isclose(joint_radius, 0.70 * min(float(value) for value in adjacent_profiles), rel_tol=1e-9, abs_tol=1e-12) or any(joint_radius >= float(value) for value in adjacent_profiles):
                    raise SurfacePreviewPublishError(f"{joint_where} radius is not a narrowed adjacent-profile station")
            distal_section = ordered_sections[-1]
            if distal_section["points"][1] != joint["mass"]["center"]:
                raise SurfacePreviewPublishError(f"{joint_where} must coincide with the distal limb endpoint")
            if joint["name"] == "hock":
                hock_centers[tuple(parsed_owner["anchors"])] = joint["mass"]["center"]
                hock_records[tuple(parsed_owner["anchors"])] = (joint, ordered_sections)
                anchor = anchor_by_owner_key.get(owner_key)
                if anchor is None or anchor["point"] != joint["mass"]["center"]:
                    raise SurfacePreviewPublishError(f"{joint_where} does not bind the hock anchor")
            joint_records.append((parsed_owner, joint, ordered_sections))
    if {role: limb_roles.count(role) for role in section_by_role} != {"upper_arm": 2, "forearm": 2, "thigh": 2, "shin": 2}:
        raise SurfacePreviewPublishError("regional guide limb owner counts are invalid")
    for parsed_owner, joint, ordered_sections in joint_records:
        role = parsed_owner["role"]
        if role not in {"upper_arm", "thigh"}:
            continue
        neighbor_role = "forearm" if role == "upper_arm" else "shin"
        neighbor_key = next(
            (
                key for key, value in limb_by_owner_key.items()
                if value["owner"]["namespace"] == parsed_owner["namespace"]
                and value["owner"]["anchors"] == parsed_owner["anchors"]
                and value["owner"]["kind"] == parsed_owner["kind"]
                and value["owner"]["role"] == neighbor_role
            ),
            None,
        )
        if neighbor_key is None:
            raise SurfacePreviewPublishError(f"{role} joint has no matching neighboring limb")
        neighbor = limb_by_owner_key[neighbor_key]
        expected_adjacent = [float(ordered_sections[-1]["thickness"][1]), float(neighbor["sections"][0]["thickness"][0])]
        actual_adjacent = [float(value) for value in joint["adjacent_profiles"]]
        if actual_adjacent != expected_adjacent:
            raise SurfacePreviewPublishError(f"{role} joint adjacent profiles do not bind neighboring limb sections")

    # Cross-check the shoulder sidecar against the already validated upper-arm
    # controls.  Local JSON shape validation alone would allow a plausible but
    # disconnected frame to pass publication.
    upper_arms = {
        tuple(item["owner"]["anchors"]): item
        for item in limbs
        if isinstance(item, dict) and item.get("owner", {}).get("role") == "upper_arm"
    }
    central_anchor = [_finite_number(value, f"regional-guide.controls.shoulder_frame.central.anchor[{index}]") for index, value in enumerate(central["anchor"])]
    central_profile = [_finite_number(value, f"regional-guide.controls.shoulder_frame.central.profile[{index}]") for index, value in enumerate(profile)]
    for side_index, side in enumerate(sides):
        where = f"regional-guide.controls.shoulder_frame.sides[{side_index}]"
        side_name = side["side"]
        expected_records = expected_control_records[side_name]
        upper_arm = upper_arms.get((side_name,))
        if upper_arm is None:
            raise SurfacePreviewPublishError(f"{where} has no matching upper-arm guide")
        first_section = {section["control"]: section for section in upper_arm["sections"]}.get("pre-joint")
        if first_section is None:
            raise SurfacePreviewPublishError(f"{where} upper-arm guide has no pre-joint section")
        socket = side["socket"]["point"]
        close_point(
            socket,
            first_section["points"][0],
            f"{where}.socket-to-upper-arm-root",
        )
        extremum = side["extremum"]["point"]
        expected_span = abs(float(extremum[0]) - central_anchor[0])
        if expected_span <= 0.0:
            raise SurfacePreviewPublishError(f"{where} declared shoulder span is degenerate")
        expected_slope = (float(extremum[1]) - central_anchor[1]) / expected_span
        if not math.isclose(float(side["span"]), expected_span, rel_tol=1.0e-9, abs_tol=1.0e-12) or not math.isclose(float(side["slope"]), expected_slope, rel_tol=1.0e-9, abs_tol=1.0e-12):
            raise SurfacePreviewPublishError(f"{where} span and slope do not derive from central anchor and extremum")
        curves_by_name = {curve["name"]: curve for curve in side["curves"]}
        anterior = curves_by_name["anterior-support"]
        posterior = curves_by_name["posterior-return"]
        deltoid = curves_by_name["deltoid-sweep"]
        for curve_name, curve in (("anterior-support", anterior), ("posterior-return", posterior), ("deltoid-sweep", deltoid)):
            points = curve["points"]
            if any(points[index] == points[index + 1] for index in range(len(points) - 1)):
                raise SurfacePreviewPublishError(f"{where}.{curve_name} has a degenerate adjacent control")
        for curve_name, curve in (("anterior-support", anterior), ("posterior-return", posterior)):
            points = curve["points"]
            close_point(points[0], central_anchor, f"{where}.{curve_name}.start")
            close_point(points[2], extremum, f"{where}.{curve_name}.extremum")
            close_point(points[3], socket, f"{where}.{curve_name}.socket")
        peak_anchor = [float(value) for value in side["peak_anchor"]]
        axilla_anchor = [float(value) for value in side["axilla_anchor"]]
        wrap_anchor = [
            peak_anchor[0],
            0.5 * (peak_anchor[1] + axilla_anchor[1]),
            0.5 * (peak_anchor[2] + axilla_anchor[2]),
        ]
        depth_radius = float(expected_records["depth_radius"])
        close_point(
            anterior["points"][1],
            [wrap_anchor[0], wrap_anchor[1], wrap_anchor[2] + depth_radius],
            f"{where}.anterior-support.authored-depth-wrap",
        )
        close_point(
            posterior["points"][1],
            [wrap_anchor[0], wrap_anchor[1], wrap_anchor[2] - depth_radius],
            f"{where}.posterior-return.authored-depth-wrap",
        )
        close_point(deltoid["points"][0], extremum, f"{where}.deltoid-sweep.extremum")
        close_point(deltoid["points"][1], socket, f"{where}.deltoid-sweep.socket")
        first_start = first_section["points"][0]
        first_end = first_section["points"][1]
        first_quarter = [float(first_start[index]) + 0.25 * (float(first_end[index]) - float(first_start[index])) for index in range(3)]
        close_point(deltoid["points"][2], first_quarter, f"{where}.deltoid-sweep.first-quarter")
        anterior_profile = [float(value) for value in anterior["profile"]]
        posterior_profile = [float(value) for value in posterior["profile"]]
        deltoid_profile = [float(value) for value in deltoid["profile"]]
        if not math.isclose(anterior_profile[0], central_profile[0], rel_tol=1.0e-9, abs_tol=1.0e-12) or not math.isclose(posterior_profile[0], central_profile[1], rel_tol=1.0e-9, abs_tol=1.0e-12):
            raise SurfacePreviewPublishError(f"{where} support profiles do not bind the central profile")
        if anterior_profile[1:] != posterior_profile[1:]:
            raise SurfacePreviewPublishError(f"{where} support profiles do not share their rejoin controls")
        arm_thickness = [float(value) for value in first_section["thickness"]]
        arm_profile = [float(value) for value in upper_arm["profile_controls"]]
        if not math.isclose(anterior_profile[-1], arm_profile[0], rel_tol=1.0e-9, abs_tol=1.0e-12) or not math.isclose(anterior_profile[-1], arm_thickness[0], rel_tol=1.0e-9, abs_tol=1.0e-12):
            raise SurfacePreviewPublishError(f"{where} support profile does not bind the upper-arm root")
        if not math.isclose(deltoid_profile[0], anterior_profile[2], rel_tol=1.0e-9, abs_tol=1.0e-12) or not math.isclose(deltoid_profile[1], arm_profile[0], rel_tol=1.0e-9, abs_tol=1.0e-12) or not math.isclose(deltoid_profile[2], arm_profile[1], rel_tol=1.0e-9, abs_tol=1.0e-12) or deltoid_profile[1] != arm_thickness[0] or deltoid_profile[2] != arm_thickness[1]:
            raise SurfacePreviewPublishError(f"{where} deltoid profile does not bind the upper-arm profile")

    paws = controls["paws"]
    if not isinstance(paws, list) or len(paws) != 4:
        raise SurfacePreviewPublishError("regional guide paw controls are invalid")
    paw_owner_keys: set[str] = set()
    paw_roles: list[str] = []
    for index, item in enumerate(paws):
        if not isinstance(item, dict) or not {"owner"} <= set(item):
            raise SurfacePreviewPublishError(f"regional guide paws[{index}] has an invalid shape")
        parsed_owner = owner(item["owner"], f"regional-guide.controls.paws[{index}].owner")
        if parsed_owner["role"] not in {"hand", "foot"}:
            raise SurfacePreviewPublishError(f"regional guide paws[{index}] owner role is invalid")
        owner_key = json.dumps(parsed_owner, sort_keys=True)
        if owner_key in paw_owner_keys:
            raise SurfacePreviewPublishError(f"regional guide paws[{index}] owner is duplicated")
        paw_owner_keys.add(owner_key)
        paw_roles.append(parsed_owner["role"])
        where = f"regional-guide.controls.paws[{index}]"
        if parsed_owner["role"] == "hand":
            expected_keys = {"owner", "masses", "attachment", "attachment_source"}
            if set(item) != expected_keys:
                raise SurfacePreviewPublishError(f"{where} has an invalid hand shape")
            _mass_list(item["masses"], f"{where}.masses", lower, upper, {"paw"})
            _path(item["attachment"], f"{where}.attachment", lower, upper, {"attachment"}, expected_kind="capsule")
            source_value = item["attachment_source"]
            source_where = f"{where}.attachment_source"
        else:
            expected_keys = {"owner", "chain", "hock_source"}
            if set(item) != expected_keys:
                raise SurfacePreviewPublishError(f"{where} has an invalid foot shape")
            chain = item["chain"]
            if not isinstance(chain, dict) or set(chain) != {"hock", "metatarsal", "masses", "contact_height", "axes", "midpoints", "authored_profile"}:
                raise SurfacePreviewPublishError(f"{where}.chain has an invalid shape")
            _mass(chain["hock"], f"{where}.chain.hock", lower, upper, {"hock-anchor"})
            _path(chain["metatarsal"], f"{where}.chain.metatarsal", lower, upper, {"metatarsal"}, expected_kind="tapered-segment")
            _mass_list(chain["masses"], f"{where}.chain.masses", lower, upper, {"paw-pad", "toe-box"})
            axes = chain["axes"]
            if axes != {"lateral": [1.0, 0.0, 0.0], "up": [0.0, 1.0, 0.0], "forward": [0.0, 0.0, 1.0]}:
                raise SurfacePreviewPublishError(f"{where}.chain.axes are invalid")
            contact_height = _finite_number(chain["contact_height"], f"{where}.chain.contact_height")
            chain_masses = {mass["control"]: mass for mass in chain["masses"]}
            hock = chain["hock"]
            metatarsal = chain["metatarsal"]
            pad = chain_masses["paw-pad"]
            toe = chain_masses["toe-box"]
            if metatarsal["points"][0] != hock["center"] or metatarsal["points"][1] != pad["center"]:
                raise SurfacePreviewPublishError(f"{where}.chain.metatarsal does not bind hock to pad")
            if metatarsal["points"][1][2] <= metatarsal["points"][0][2] or metatarsal["points"][1][1] >= metatarsal["points"][0][1]:
                raise SurfacePreviewPublishError(f"{where}.chain.metatarsal must descend forward from hock")
            if toe["center"][2] <= pad["center"][2] or not float(metatarsal["thickness"][0]) > float(metatarsal["thickness"][-1]):
                raise SurfacePreviewPublishError(f"{where}.chain controls have invalid order or taper")
            if not math.isclose(pad["center"][1] - pad["radii"][1], contact_height, rel_tol=0.0, abs_tol=1.0e-12) or not math.isclose(toe["center"][1] - toe["radii"][1], contact_height, rel_tol=0.0, abs_tol=1.0e-12):
                raise SurfacePreviewPublishError(f"{where}.chain masses do not share the contact datum")
            _require_axis_aligned_overlap(pad, toe, f"{where}.chain.pad-toe")
            midpoints = chain["midpoints"]
            if not isinstance(midpoints, dict) or set(midpoints) != {"metatarsal", "pad_toe"}:
                raise SurfacePreviewPublishError(f"{where}.chain.midpoints has an invalid shape")
            midpoint_specs = (
                ("metatarsal", hock, pad),
                ("pad_toe", pad, toe),
            )
            for midpoint_name, start_mass, end_mass in midpoint_specs:
                midpoint_where = f"{where}.chain.midpoints.{midpoint_name}"
                midpoint = midpoints[midpoint_name]
                if not isinstance(midpoint, dict) or set(midpoint) != {"center", "radii"}:
                    raise SurfacePreviewPublishError(f"{midpoint_where} has an invalid shape")
                midpoint_center = _point(midpoint["center"], f"{midpoint_where}.center")
                midpoint_radii = _point(midpoint["radii"], f"{midpoint_where}.radii")
                expected_center = [
                    0.5 * (float(start_mass["center"][axis]) + float(end_mass["center"][axis]))
                    for axis in range(3)
                ]
                expected_radii = [
                    0.5 * (float(start_mass["radii"][axis]) + float(end_mass["radii"][axis]))
                    for axis in range(3)
                ]
                if midpoint_center != expected_center or midpoint_radii != expected_radii:
                    raise SurfacePreviewPublishError(f"{midpoint_where} is not the exact derived center/full radii midpoint")
            if not isinstance(chain["authored_profile"], dict):
                raise SurfacePreviewPublishError(f"{where}.chain.authored_profile is invalid")
            source_value = item["hock_source"]
            source_where = f"{where}.hock_source"
        if not isinstance(source_value, dict) or set(source_value) != {"owner", "anchor", "point", "boundary_point"}:
            raise SurfacePreviewPublishError(f"{source_where} has an invalid shape")
        source_owner = owner(source_value["owner"], f"{source_where}.owner")
        expected_parent_role = "forearm" if parsed_owner["role"] == "hand" else "shin"
        expected_anchor = "forearm-distal-boundary" if parsed_owner["role"] == "hand" else "hock-endpoint"
        if source_owner["role"] != expected_parent_role or source_owner["anchors"] != parsed_owner["anchors"]:
            raise SurfacePreviewPublishError(f"{source_where}.owner does not match the paw parent")
        if source_value["anchor"] != expected_anchor:
            raise SurfacePreviewPublishError(f"{source_where}.anchor is invalid")
        source_point = _point(source_value["point"], f"{source_where}.point")
        boundary_point = _point(source_value["boundary_point"], f"{source_where}.boundary_point")
        if parsed_owner["role"] == "hand" and source_point != item["attachment"]["points"][0]:
            raise SurfacePreviewPublishError(f"{source_where}.point does not match the attachment start")
        if parsed_owner["role"] == "foot" and source_point != item["chain"]["hock"]["center"]:
            raise SurfacePreviewPublishError(f"{source_where}.point does not match the hock anchor")
        parent_key = json.dumps(source_owner, sort_keys=True)
        parent_limb = limb_by_owner_key.get(parent_key)
        if parent_limb is None:
            raise SurfacePreviewPublishError(f"{source_where}.owner has no matching limb guide")
        parent_sections = {section["control"]: section for section in parent_limb["sections"]}
        parent_last = parent_sections[section_order_by_role[source_owner["role"]][-1]]
        expected_boundary = parent_last["points"][1]
        if boundary_point != expected_boundary:
            raise SurfacePreviewPublishError(f"{source_where}.boundary_point does not match the parent distal endpoint")
        parent_anchor = anchor_by_owner_key.get(parent_key)
        if parent_anchor is None or parent_anchor["name"] != source_value["anchor"]:
            raise SurfacePreviewPublishError(f"{source_where} does not name a compiled parent anchor")
        if source_point != parent_anchor["point"] or boundary_point != parent_anchor["boundary_point"]:
            raise SurfacePreviewPublishError(f"{source_where} does not match the compiled parent anchor")
        if parsed_owner["role"] == "hand":
            masses = {mass["control"]: mass for mass in item["masses"]}
            if item["attachment"]["points"][1] != masses["paw"]["center"]:
                raise SurfacePreviewPublishError(f"{where}.attachment must terminate at its source-owned mass")
        else:
            hock = item["chain"]["hock"]
            hock_record = hock_records.get(tuple(parsed_owner["anchors"]))
            if hock_record is None:
                raise SurfacePreviewPublishError(f"{where} has no matching source-owned hock")
            hock_joint, hock_sections = hock_record
            if hock["radii"] != hock_joint["mass"]["radii"]:
                raise SurfacePreviewPublishError(f"{where}.chain hock radii do not bind the compiled shin hock")
            metatarsal = item["chain"]["metatarsal"]
            expected_hock_profiles = [float(hock_sections[-1]["thickness"][1]), float(metatarsal["thickness"][0])]
            if [float(value) for value in hock_joint["adjacent_profiles"]] != expected_hock_profiles:
                raise SurfacePreviewPublishError(f"{where}.chain hock adjacent profiles do not bind the metatarsal")
            if source_point != hock["center"] or source_point != hock_centers.get(tuple(parsed_owner["anchors"]), []):
                raise SurfacePreviewPublishError(f"{where}.hock source is inconsistent")
    if {role: paw_roles.count(role) for role in {"hand", "foot"}} != {"hand": 2, "foot": 2}:
        raise SurfacePreviewPublishError("regional guide paw owner counts are invalid")

    _validate_foot_profile_controls(
        controls["foot_profile"],
        controls,
        lower,
        upper,
        variant_id=variant_id,
        profile_context=profile_context,
        producer_payload=producer_payload,
    )

    tails = controls["tails"]
    if not isinstance(tails, list) or len(tails) != 2:
        raise SurfacePreviewPublishError("regional guide tail controls are invalid")
    tail_owner_keys: set[str] = set()
    tail_roles: list[str] = []
    for index, item in enumerate(tails):
        if not isinstance(item, dict) or set(item) != {"owner", "centerline", "sections", "masses"}:
            raise SurfacePreviewPublishError(f"regional guide tails[{index}] has an invalid shape")
        parsed_owner = owner(item["owner"], f"regional-guide.controls.tails[{index}].owner")
        if parsed_owner["role"] not in {"tail_root", "tail_tip"}:
            raise SurfacePreviewPublishError(f"regional guide tails[{index}] owner role is invalid")
        owner_key = json.dumps(parsed_owner, sort_keys=True)
        if owner_key in tail_owner_keys:
            raise SurfacePreviewPublishError(f"regional guide tails[{index}] owner is duplicated")
        tail_owner_keys.add(owner_key)
        tail_roles.append(parsed_owner["role"])
        _path(item["centerline"], f"regional-guide.controls.tails[{index}].centerline", lower, upper, {"segment"}, expected_kind="tapered-segment")
        sections = {"root-attachment"} if parsed_owner["role"] == "tail_root" else {"tip-extension"}
        masses = {"root-collar"} if parsed_owner["role"] == "tail_root" else {"tip-cap"}
        _path_list(item["sections"], f"regional-guide.controls.tails[{index}].sections", lower, upper, sections, expected_kind="tapered-segment")
        _mass_list(item["masses"], f"regional-guide.controls.tails[{index}].masses", lower, upper, masses)
    if set(tail_roles) != {"tail_root", "tail_tip"}:
        raise SurfacePreviewPublishError("regional guide tail owner counts are invalid")


def _validate_guide(
    path: Path,
    entry: dict[str, Any],
    *,
    variant_id: str,
    manifest: dict[str, Any],
    descriptor_addresses: list[dict[str, Any]],
    producer_payload: dict[str, Any],
) -> dict[str, Any]:
    guide = _read_json(path, MAX_GUIDE_BYTES, "regional-guide.json")
    _finite_json(guide, "regional-guide.json")
    expected_fields = {"format", "variant", "owners", "counts", "projections", "shared_render_bounds", "canvas", "layout", "controls", "boundary"}
    if set(guide) != expected_fields or guide.get("format") != REGIONAL_GUIDE_FORMAT or guide.get("variant") != variant_id:
        raise SurfacePreviewPublishError("regional guide has unsupported format, variant, or fields")
    if entry.get("format") != REGIONAL_GUIDE_FORMAT or entry.get("variant") != variant_id:
        raise SurfacePreviewPublishError("regional guide inventory metadata is invalid")
    owners = guide.get("owners")
    if not isinstance(owners, list) or len(owners) != EXPECTED_GUIDE_COUNTS["owners"]:
        raise SurfacePreviewPublishError("regional guide owners count is invalid")
    normalized_owners = [_validate_address(item, f"regional-guide.owners[{index}]") for index, item in enumerate(owners)]
    if len({json.dumps(item, sort_keys=True) for item in normalized_owners}) != len(normalized_owners):
        raise SurfacePreviewPublishError("regional guide owners must be unique")
    if sorted(normalized_owners, key=_address_sort_key) != sorted(descriptor_addresses, key=_address_sort_key):
        raise SurfacePreviewPublishError("regional guide owners do not match source descriptors")
    counts = guide.get("counts")
    if counts != EXPECTED_GUIDE_COUNTS:
        raise SurfacePreviewPublishError("regional guide counts are invalid")
    bounds = guide.get("shared_render_bounds")
    if bounds != manifest.get("shared_render_bounds"):
        raise SurfacePreviewPublishError("regional guide bounds do not match manifest")
    if not isinstance(bounds, dict) or set(bounds) != {"min", "max"}:
        raise SurfacePreviewPublishError("regional guide bounds are invalid")
    lower, upper = bounds["min"], bounds["max"]
    if not isinstance(lower, list) or not isinstance(upper, list) or len(lower) != 3 or len(upper) != 3:
        raise SurfacePreviewPublishError("regional guide bounds are not finite ordered triples")
    lower = [_finite_number(item, f"regional-guide.shared_render_bounds.min[{index}]") for index, item in enumerate(lower)]
    upper = [_finite_number(item, f"regional-guide.shared_render_bounds.max[{index}]") for index, item in enumerate(upper)]
    if any(a >= b for a, b in zip(lower, upper)):
        raise SurfacePreviewPublishError("regional guide bounds are not finite ordered triples")
    if guide.get("projections") != manifest.get("projections") or guide.get("layout") != manifest.get("layout") or guide.get("canvas") != manifest.get("canvas"):
        raise SurfacePreviewPublishError("regional guide framing does not match manifest")
    if guide.get("canvas") != EXPECTED_CANVAS or guide.get("projections") != EXPECTED_PROJECTIONS or guide.get("layout") != EXPECTED_LAYOUT:
        raise SurfacePreviewPublishError("regional guide framing is not the fixed v3 layout")
    _validate_controls(
        guide.get("controls"),
        normalized_owners,
        lower,
        upper,
        variant_id=variant_id,
        producer_payload=producer_payload,
    )
    if guide.get("boundary") != "private disposable regional controls; source-owned AddressKeys only; not a semantic or runtime contract":
        raise SurfacePreviewPublishError("regional guide boundary is invalid")
    return guide


def _validate_bundle(
    bundle: Path,
    expected_source_sha256: str,
    producer_payload: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    try:
        bundle_info = bundle.lstat()
    except OSError as exc:
        raise SurfacePreviewPublishError("surface bundle root is unavailable") from exc
    if stat.S_ISLNK(bundle_info.st_mode) or not stat.S_ISDIR(bundle_info.st_mode):
        raise SurfacePreviewPublishError("surface bundle root must be a real non-symlink directory")
    manifest_path = bundle / MANIFEST_NAME
    manifest = _read_json(manifest_path, MAX_MANIFEST_BYTES, MANIFEST_NAME)
    _finite_json(manifest, MANIFEST_NAME)
    if manifest.get("format") != SURFACE_PREVIEW_FORMAT or manifest.get("status") != "success":
        raise SurfacePreviewPublishError("surface bundle has unsupported format or status")
    expected_manifest_fields = {"format", "status", "source_format", "source", "shared_render_bounds", "canvas", "layout", "projections", "generator", "variants"}
    if set(manifest) != expected_manifest_fields:
        raise SurfacePreviewPublishError("surface bundle has unknown manifest fields")
    if manifest.get("source_format") != common.PROVISIONAL_FORM_FORMAT:
        raise SurfacePreviewPublishError("surface bundle source_format must be provisional-form v11")
    source = manifest.get("source")
    if not isinstance(source, dict) or set(source) != {"format", "sha256", "document", "namespace", "resource_profile_id", "reference_scale"}:
        raise SurfacePreviewPublishError("surface bundle source must identify format and sha256")
    if source.get("format") != common.PROVISIONAL_FORM_FORMAT or source.get("sha256") != expected_source_sha256:
        raise SurfacePreviewPublishError("surface bundle source does not match the exact current producer output")
    source_hash = source.get("sha256")
    if not isinstance(source_hash, str) or len(source_hash) != 64 or any(character not in "0123456789abcdef" for character in source_hash):
        raise SurfacePreviewPublishError("surface bundle source.sha256 is invalid")
    if not all(isinstance(source.get(key), str) and source[key] for key in ("document", "namespace", "resource_profile_id")) or source["resource_profile_id"] != common.PROVISIONAL_FORM_RESOURCE_PROFILE:
        raise SurfacePreviewPublishError("surface bundle source provenance is invalid")
    _validate_reference_scale(source.get("reference_scale"), "surface bundle source.reference_scale")
    profile_binding = _validate_authored_torso_profile(producer_payload) if producer_payload is not None else None
    if producer_payload is not None:
        producer_source = producer_payload.get("source")
        producer_reference_scale = producer_payload.get("reference_scale")
        if not isinstance(producer_source, dict) or not isinstance(producer_reference_scale, dict):
            raise SurfacePreviewPublishError("surface bundle cannot bind producer provenance")
        for key in ("document", "namespace", "resource_profile_id"):
            if source[key] != producer_source.get(key):
                raise SurfacePreviewPublishError(f"surface bundle source.{key} does not match producer output")
        if source["reference_scale"] != producer_reference_scale:
            raise SurfacePreviewPublishError("surface bundle source.reference_scale does not match producer output")
    if manifest.get("canvas") != EXPECTED_CANVAS or manifest.get("projections") != EXPECTED_PROJECTIONS or manifest.get("layout") != EXPECTED_LAYOUT:
        raise SurfacePreviewPublishError("surface bundle framing is not the fixed v3 layout")
    bounds = manifest.get("shared_render_bounds")
    if not isinstance(bounds, dict) or set(bounds) != {"min", "max"}:
        raise SurfacePreviewPublishError("surface bundle shared_render_bounds is invalid")
    lower, upper = bounds["min"], bounds["max"]
    if not isinstance(lower, list) or not isinstance(upper, list) or len(lower) != 3 or len(upper) != 3 or any(type(item) not in {int, float} for item in lower + upper) or any(a >= b for a, b in zip(lower, upper)):
        raise SurfacePreviewPublishError("surface bundle shared_render_bounds is not ordered")
    generator = manifest.get("generator")
    if not isinstance(generator, dict):
        raise SurfacePreviewPublishError("surface bundle generator must be an explicit configuration object")
    required_generator = {"bundle_version", "samples_per_axis", "padding", "smooth_union", "field_primitives", "field_recipes", "ownership", "boundary", "component_visualization"}
    if set(generator) != required_generator:
        raise SurfacePreviewPublishError("surface bundle generator has missing or unknown configuration fields")
    if generator.get("bundle_version") != 3:
        raise SurfacePreviewPublishError("surface bundle generator.bundle_version must be 3")
    if type(generator.get("samples_per_axis")) is not int or not 1 <= generator["samples_per_axis"] <= 128:
        raise SurfacePreviewPublishError("surface bundle generator.samples_per_axis is out of bounds")
    if type(generator.get("padding")) not in {int, float} or not 0 <= generator["padding"] <= 100:
        raise SurfacePreviewPublishError("surface bundle generator.padding is out of bounds")
    field_primitives = generator.get("field_primitives")
    if not isinstance(field_primitives, list) or not field_primitives or len(field_primitives) > 16 or not all(isinstance(item, str) and item for item in field_primitives):
        raise SurfacePreviewPublishError("surface bundle generator.field_primitives is invalid")
    field_recipes = generator.get("field_recipes")
    if not isinstance(field_recipes, list) or not field_recipes or len(field_recipes) > 64 or not all(isinstance(item, str) and item for item in field_recipes):
        raise SurfacePreviewPublishError("surface bundle generator.field_recipes is invalid")
    if field_recipes != list(EXPECTED_FIELD_RECIPES):
        raise SurfacePreviewPublishError("surface bundle generator.field_recipes does not match the exact compiled recipe inventory")
    if generator.get("ownership") != EXPECTED_GENERATOR_OWNERSHIP:
        raise SurfacePreviewPublishError("surface bundle generator.ownership does not match the current compiled/guide-only boundary")
    if generator.get("component_visualization") != EXPECTED_COMPONENT_VISUALIZATION:
        raise SurfacePreviewPublishError("surface bundle generator.component_visualization is not the exact consumed-component visualization")
    if not isinstance(generator.get("boundary"), str) or not generator["boundary"] or len(generator["boundary"]) > 1024:
        raise SurfacePreviewPublishError("surface bundle generator.boundary is invalid")
    smooth_union = generator.get("smooth_union")
    if not isinstance(smooth_union, dict) or set(smooth_union) != {"operator", "k", "fold_order"}:
        raise SurfacePreviewPublishError("surface bundle generator.smooth_union is invalid")
    if not isinstance(smooth_union.get("operator"), str) or not isinstance(smooth_union.get("fold_order"), str):
        raise SurfacePreviewPublishError("surface bundle generator.smooth_union names are invalid")
    if type(smooth_union.get("k")) not in {int, float} or not 0 < smooth_union["k"] <= 100:
        raise SurfacePreviewPublishError("surface bundle generator.smooth_union.k is out of bounds")
    try:
        generator_config = common._metadata(generator, "surface bundle generator", max_len=8192)
    except ValidationError as exc:
        raise SurfacePreviewPublishError(str(exc)) from exc
    variants = manifest.get("variants")
    if not isinstance(variants, list) or len(variants) != len(EXPECTED_VARIANTS) or any(not isinstance(item, dict) for item in variants) or {item.get("id") for item in variants} != set(EXPECTED_VARIANTS) or len({item.get("id") for item in variants}) != len(EXPECTED_VARIANTS):
        raise SurfacePreviewPublishError("surface bundle variants must contain the exact canonical current-format variant ids")
    inventory_paths: set[str] = set()
    published: list[dict[str, Any]] = []
    validated_guides: dict[str, dict[str, Any]] = {}
    producer_variants = producer_payload.get("variants") if producer_payload is not None else None
    producer_by_id = {item.get("id"): item for item in producer_variants} if isinstance(producer_variants, list) and all(isinstance(item, dict) for item in producer_variants) else {}
    if producer_payload is not None and (not isinstance(producer_variants, list) or len(producer_by_id) != len(EXPECTED_VARIANTS) or set(producer_by_id) != set(EXPECTED_VARIANTS)):
        raise SurfacePreviewPublishError("surface bundle variants cannot bind producer output")
    for index, variant in enumerate(variants):
        where = f"variants[{index}]"
        if not isinstance(variant, dict):
            raise SurfacePreviewPublishError(f"{where} must be an object")
        if set(variant) != {"id", "profile_id", "source", "descriptor_address_keys", "grid", "metrics", "inventory"}:
            raise SurfacePreviewPublishError(f"{where} has unknown or missing fields")
        if variant.get("profile_id") != variant.get("id"):
            raise SurfacePreviewPublishError(f"{where}.profile_id must equal id")
        variant_source = variant.get("source")
        if not isinstance(variant_source, dict) or set(variant_source) != {"document", "namespace", "resource_profile_id"}:
            raise SurfacePreviewPublishError(f"{where}.source provenance is invalid")
        if variant_source != {key: source[key] for key in ("document", "namespace", "resource_profile_id")}:
            raise SurfacePreviewPublishError(f"{where}.source provenance does not match manifest")
        producer_variant = producer_by_id.get(variant.get("id")) if producer_variants is not None else None
        if producer_variant is not None:
            if not isinstance(producer_variant, dict) or producer_variant.get("id") != variant["id"]:
                raise SurfacePreviewPublishError(f"{where} does not match producer variant")
            expected_descriptor_addresses = sorted([item.get("address") for item in producer_variant.get("descriptors", [])], key=_address_sort_key) if isinstance(producer_variant.get("descriptors"), list) else None
            actual_descriptor_addresses = sorted(variant.get("descriptor_address_keys", []), key=_address_sort_key) if isinstance(variant.get("descriptor_address_keys"), list) else None
            if expected_descriptor_addresses is None or actual_descriptor_addresses != expected_descriptor_addresses:
                raise SurfacePreviewPublishError(f"{where}.descriptor_address_keys do not match producer output")
        descriptor_addresses = variant.get("descriptor_address_keys")
        if not isinstance(descriptor_addresses, list) or len(descriptor_addresses) != EXPECTED_GUIDE_COUNTS["owners"]:
            raise SurfacePreviewPublishError(f"{where}.descriptor_address_keys is invalid")
        descriptor_addresses = [_validate_address(item, f"{where}.descriptor_address_keys[{i}]") for i, item in enumerate(descriptor_addresses)]
        if len({json.dumps(item, sort_keys=True) for item in descriptor_addresses}) != len(descriptor_addresses):
            raise SurfacePreviewPublishError(f"{where}.descriptor_address_keys contains duplicates")
        if any(item["namespace"] != source["namespace"] for item in descriptor_addresses):
            raise SurfacePreviewPublishError(f"{where}.descriptor_address_keys namespace differs from source")
        inventory = variant.get("inventory")
        if not isinstance(inventory, list) or len(inventory) != 5:
            raise SurfacePreviewPublishError(f"{where}.inventory must contain exactly five artifacts")
        expected_inventory_kinds = ["ply", "semantic-sidecar", "metrics", "guide-skin-composite-png", "regional-guide-json"]
        if [item.get("kind") for item in inventory if isinstance(item, dict)] != expected_inventory_kinds:
            raise SurfacePreviewPublishError(f"{where}.inventory is not the canonical v3 order")
        expected_inventory_paths = {
            "ply": f"{variant['id']}/surface.ply",
            "semantic-sidecar": f"{variant['id']}/semantic.json",
            "metrics": f"{variant['id']}/metrics.json",
            "guide-skin-composite-png": f"{variant['id']}/guide-skin-composite.png",
            "regional-guide-json": f"{variant['id']}/regional-guide.json",
        }
        kinds: set[str] = set()
        image_entry: dict[str, Any] | None = None
        metrics_payload: dict[str, Any] | None = None
        guide_payload: dict[str, Any] | None = None
        for entry_index, entry in enumerate(inventory):
            entry_where = f"{where}.inventory[{entry_index}]"
            if not isinstance(entry, dict):
                raise SurfacePreviewPublishError(f"{entry_where} must be an object")
            kind = entry.get("kind")
            if kind not in {"ply", "semantic-sidecar", "metrics", "guide-skin-composite-png", "regional-guide-json"} or kind in kinds:
                raise SurfacePreviewPublishError(f"{entry_where}.kind is missing or duplicated")
            base_entry_fields = {"kind", "path", "sha256", "bytes"}
            extra_entry_fields = {
                "guide-skin-composite-png": {"width", "height", "views", "panels_per_view", "mode"},
                "regional-guide-json": {"format", "variant"},
            }.get(kind, set())
            if set(entry) != base_entry_fields | extra_entry_fields:
                raise SurfacePreviewPublishError(f"{entry_where} has unknown or missing fields")
            kinds.add(kind)
            rel = _safe_relative(entry.get("path"), f"{entry_where}.path")
            rel_text = rel.as_posix()
            if rel_text != expected_inventory_paths[kind]:
                raise SurfacePreviewPublishError(f"{entry_where}.path is not the canonical v3 artifact path")
            if rel_text in inventory_paths or rel_text == MANIFEST_NAME:
                raise SurfacePreviewPublishError(f"duplicate or reserved inventory path: {rel_text}")
            inventory_paths.add(rel_text)
            artifact = bundle / rel
            if artifact.is_symlink() or not artifact.is_file():
                raise SurfacePreviewPublishError(f"{entry_where}.path is not a regular file")
            if type(entry.get("bytes")) is not int or entry["bytes"] < 0:
                raise SurfacePreviewPublishError(f"{entry_where}.bytes is invalid")
            if not isinstance(entry.get("sha256"), str) or len(entry["sha256"]) != 64:
                raise SurfacePreviewPublishError(f"{entry_where}.sha256 is invalid")
            actual_hash, actual_size = _sha256(artifact, rel_text)
            if actual_hash != entry["sha256"] or actual_size != entry["bytes"]:
                raise SurfacePreviewPublishError(f"inventory does not match {rel_text}")
            if kind == "guide-skin-composite-png":
                image_entry = entry
                _validate_png(artifact, entry, rel_text)
            elif kind == "metrics":
                parsed_metrics = _read_json(artifact, MAX_METRICS_BYTES, f"{where}.metrics.json")
                _finite_json(parsed_metrics, f"{where}.metrics.json")
                if not isinstance(parsed_metrics, dict):
                    raise SurfacePreviewPublishError(f"{where}.metrics.json must be an object")
                metrics_payload = parsed_metrics
            elif kind == "regional-guide-json":
                if producer_payload is None:
                    raise SurfacePreviewPublishError(
                        f"{where}.regional-guide.json cannot bind producer output"
                    )
                guide_payload = _validate_guide(
                    artifact,
                    entry,
                    variant_id=variant["id"],
                    manifest=manifest,
                    descriptor_addresses=descriptor_addresses,
                    producer_payload=producer_payload,
                )
        if kinds != {"ply", "semantic-sidecar", "metrics", "guide-skin-composite-png", "regional-guide-json"} or image_entry is None or metrics_payload is None or guide_payload is None:
            raise SurfacePreviewPublishError(f"{where}.inventory has wrong artifact kinds")
        validated_guides[variant["id"]] = guide_payload
        if variant.get("metrics") != metrics_payload:
            raise SurfacePreviewPublishError(f"{where}.metrics does not match the inventoried metrics.json")
        _validate_component_visualization_metrics(
            metrics_payload,
            allowed_owners=descriptor_addresses,
            expected_component_count=EXPECTED_GUIDE_COUNTS["compiled_fields"],
            expected_recipe_counts=EXPECTED_GUIDE_COUNTS["compiled_field_recipe_counts"],
            where=where,
        )
        guide_counts = guide_payload["counts"]
        if metrics_payload.get("generated_field_count") != guide_counts["compiled_fields"]:
            raise SurfacePreviewPublishError(f"{where}.metrics.generated_field_count does not match the regional guide")
        if metrics_payload.get("field_recipe_counts") != guide_counts["compiled_field_recipe_counts"]:
            raise SurfacePreviewPublishError(f"{where}.metrics.field_recipe_counts do not match the regional guide")
        if metrics_payload.get("generated_field_count") != EXPECTED_GUIDE_COUNTS["compiled_fields"] or metrics_payload.get("field_recipe_counts") != EXPECTED_GUIDE_COUNTS["compiled_field_recipe_counts"]:
            raise SurfacePreviewPublishError(f"{where}.metrics recipe inventory does not match the expected guide counts")
        published.append({
            "id": variant["id"],
            "entry": image_entry,
            "binding": {
                "source": {
                    "format": common.PROVISIONAL_FORM_FORMAT,
                    "sha256": expected_source_sha256,
                    "document": source["document"],
                    "namespace": source["namespace"],
                    "resource_profile_id": source["resource_profile_id"],
                },
                "reference_scale": source["reference_scale"],
                "variant_id": variant["id"],
                "profile_id": variant["profile_id"],
                "producer_variant_sha256": profile_binding["variants"][variant["id"]]["producer_variant_sha256"] if profile_binding else None,
                "descriptor_owners": sorted(descriptor_addresses, key=_address_sort_key),
                "capture": {key: manifest[key] for key in ("canvas", "projections", "layout", "shared_render_bounds")},
                "torso_lineage": profile_binding["variants"][variant["id"]]["torso_lineage"] if profile_binding else None,
                "head_neck_lineage": profile_binding["variants"][variant["id"]]["head_neck_lineage"] if profile_binding else None,
                "arm_lineage": profile_binding["variants"][variant["id"]]["arm_lineage"] if profile_binding else None,
                "leg_lineage": profile_binding["variants"][variant["id"]]["leg_lineage"] if profile_binding else None,
            },
        })
    actual_paths, actual_directories = _regular_artifacts(bundle)
    actual_paths -= {MANIFEST_NAME}
    if actual_paths != inventory_paths or actual_directories != set(EXPECTED_VARIANTS):
        raise SurfacePreviewPublishError("surface bundle contains unlisted or missing regular output")
    return published, {
        "source": {"format": source["format"], "sha256": source_hash},
        "generator": generator_config,
        "regional_guides": validated_guides,
    }


SUCCESSOR_EXTREMITY_ORDER = (
    "left-hand-attachment", "left-hand-paw", "left-foot",
    "right-hand-attachment", "right-hand-paw", "right-foot",
)
SUCCESSOR_EXTREMITY_KINDS = (
    "hand-attachment", "hand-paw", "foot-chain",
    "hand-attachment", "hand-paw", "foot-chain",
)
SUCCESSOR_HEAD_NECK_ORDER = (
    "vertical-neck-cranium", "forward-muzzle",
)
SUCCESSOR_HEAD_NECK_SECTION_COUNTS = (5, 4)
SUCCESSOR_LIMB_ORDER = (
    "left-upper-arm-route", "left-forearm-route",
    "right-upper-arm-route", "right-forearm-route",
    "left-leg", "right-leg",
)
SUCCESSOR_LIMB_STATION_NAMES = (
    ("upper-arm-start", "upper-arm-midpoint", "elbow"),
    ("elbow", "forearm-midpoint", "forearm-distal"),
    ("upper-arm-start", "upper-arm-midpoint", "elbow"),
    ("elbow", "forearm-midpoint", "forearm-distal"),
    ("thigh-start", "thigh-midpoint", "knee", "shin-midpoint", "hock-endpoint"),
    ("thigh-start", "thigh-midpoint", "knee", "shin-midpoint", "hock-endpoint"),
)
SUCCESSOR_EXTREMITY_STATION_NAMES = (
    ("hand-attachment-start", "hand-attachment-end"),
    ("hand-paw-base", "hand-paw-palm", "hand-paw-knuckle", "hand-paw-tip"),
    ("hock", "metatarsal-midpoint", "pad", "pad-toe-midpoint", "toe"),
    ("hand-attachment-start", "hand-attachment-end"),
    ("hand-paw-base", "hand-paw-palm", "hand-paw-knuckle", "hand-paw-tip"),
    ("hock", "metatarsal-midpoint", "pad", "pad-toe-midpoint", "toe"),
)
SUCCESSOR_TAIL_SECTION_NAMES = (
    ("tail-root-source-start", "tail-root-source-end"),
    ("tail-root-attachment-start", "tail-root-attachment-end"),
    ("tail-root-collar-section-0", "tail-root-collar-section-1", "tail-root-collar-section-2"),
    ("tail-tip-source-start", "tail-tip-source-end"),
    ("tail-tip-extension-start", "tail-tip-extension-end"),
    ("tail-tip-cap-section-0", "tail-tip-cap-section-1", "tail-tip-cap-section-2"),
)
SUCCESSOR_REPLACED_BASELINE_RECIPES = (
    "torso-cage", "cranium", "muzzle", "head-base-bridge", "tapered-neck", "neck-collar",
    "deltoid-sweep-1",
    "upper_arm-pre-joint", "upper_arm-joint", "forearm-proximal", "forearm-distal",
    "thigh-pre-joint", "thigh-joint", "shin-pre-joint", "shin-joint", "elbow", "knee", "hock",
    "paw", "extremity-bridge", "metatarsal", "paw-pad", "toe-box",
    "tail-segment", "tail-root-bridge", "tail-root-collar", "tail-tip-extension", "tail-tip-cap",
)
SUCCESSOR_TAIL_ORDER = (
    "tail-root-source", "tail-root-attachment", "tail-root-collar",
    "tail-tip-source", "tail-tip-extension", "tail-tip-cap",
)
SUCCESSOR_TAIL_KINDS = (
    "source-centerline", "root-attachment", "root-collar-mass",
    "source-centerline", "tip-extension", "tip-cap-mass",
)
SUCCESSOR_RETAINED_BRIDGE_RECIPES = ("hip-transition", "root-bridge")
SUCCESSOR_REPLACED_EXTREMITY_AND_TAIL_RECIPES = {
    "paw", "extremity-bridge", "metatarsal", "paw-pad", "toe-box",
    "tail-segment", "tail-root-bridge", "tail-root-collar",
    "tail-tip-extension", "tail-tip-cap",
}
SUCCESSOR_REQUIRED_REPLACED_RECIPES = (
    SUCCESSOR_REPLACED_EXTREMITY_AND_TAIL_RECIPES | {"deltoid-sweep-1"}
)


def _bounded_json(value: Any, where: str, *, depth: int = 0) -> None:
    """Keep retained experiment metadata finite and within adapter bounds."""

    if depth > 64:
        raise SurfacePreviewPublishError(f"{where} is too deeply nested")
    if type(value) in {int, float}:
        try:
            number = float(value)
        except (OverflowError, ValueError) as exc:
            raise SurfacePreviewPublishError(f"{where} is not a bounded number") from exc
        if not math.isfinite(number) or abs(number) > 1.0e12:
            raise SurfacePreviewPublishError(f"{where} is not a bounded number")
    elif isinstance(value, str):
        if len(value) > 8192:
            raise SurfacePreviewPublishError(f"{where} contains an oversized string")
    elif isinstance(value, dict):
        if len(value) > 1024:
            raise SurfacePreviewPublishError(f"{where} contains too many fields")
        for key, child in value.items():
            if not isinstance(key, str):
                raise SurfacePreviewPublishError(f"{where} contains a non-text key")
            _bounded_json(child, f"{where}.{key}", depth=depth + 1)
    elif isinstance(value, list):
        if len(value) > 10000:
            raise SurfacePreviewPublishError(f"{where} contains too many entries")
        for index, child in enumerate(value):
            _bounded_json(child, f"{where}[{index}]", depth=depth + 1)


def _source_variant_sha256(raw_variant: Any, where: str) -> str:
    """Hash one producer raw-variant using the successor's canonical framing."""

    try:
        encoded = json.dumps(
            raw_variant,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise SurfacePreviewPublishError(f"{where} cannot be canonically hashed") from exc
    return hashlib.sha256(encoded).hexdigest()


def _expected_successor_torso_controls(
    producer_payload: dict[str, Any],
    variant_id: str,
    profile_binding: dict[str, Any],
) -> list[dict[str, Any]]:
    raw_variant = next(item for item in producer_payload["variants"] if item.get("id") == variant_id)
    descriptor_by_owner = {
        _address_sort_key(item["address"]): item
        for item in raw_variant["descriptors"]
    }
    scale = math.sqrt(float(producer_payload["reference_scale"]["squared_length"]))
    controls = []
    for section in profile_binding["torso_lineage"]:
        descriptor = descriptor_by_owner.get(_address_sort_key(section["owner"]))
        if not isinstance(descriptor, dict):
            raise SurfacePreviewPublishError("successor torso metrics cannot bind its source descriptor owner")
        position = section["landmark"]["position"]
        center = [
            (float(descriptor["reference_point"][axis]) + float(position[axis])) / scale
            for axis in range(3)
        ]
        scaled = section["scaled_values_permille"]
        controls.append({
            "name": section["name"],
            "owner": section["owner"],
            "center": center,
            "axial_position": center[1],
            "lateral_radius": scaled["lateral"] / 1000.0,
            "anterior_radius": scaled["anterior"] / 1000.0,
            "posterior_radius": scaled["posterior"] / 1000.0,
        })
    return controls


def _guide_owner(guide: dict[str, Any], role: str, anchors: list[str]) -> dict[str, Any]:
    owners = [
        owner
        for owner in guide["owners"]
        if isinstance(owner, dict) and owner.get("role") == role and owner.get("anchors") == anchors
    ]
    if len(owners) != 1:
        raise SurfacePreviewPublishError(
            f"validated regional guide has no unique {anchors!r}/{role!r} source owner"
        )
    return owners[0]


def _profile_bend_count(points: list[list[float]], where: str) -> int:
    count = 0
    for index in range(1, len(points) - 1):
        previous = points[index - 1]
        center = points[index]
        following = points[index + 1]
        incoming = [float(center[axis]) - float(previous[axis]) for axis in range(3)]
        outgoing = [float(following[axis]) - float(center[axis]) for axis in range(3)]
        incoming_length = math.sqrt(sum(value * value for value in incoming))
        outgoing_length = math.sqrt(sum(value * value for value in outgoing))
        if incoming_length <= 1.0e-12 or outgoing_length <= 1.0e-12:
            continue
        alignment = sum(
            incoming[axis] * outgoing[axis] for axis in range(3)
        ) / (incoming_length * outgoing_length)
        if alignment <= -1.0 + 1.0e-8:
            raise SurfacePreviewPublishError(f"{where} reverses its ordered centerline")
        if alignment < 1.0 - 1.0e-8:
            count += 1
    return count


def _expected_successor_head_neck_metadata(guide: dict[str, Any]) -> dict[str, Any]:
    """Re-derive the v9 head/neck sidecar from the validated v11 guide."""

    head = guide["controls"]["head"]
    sections = head["sections"]
    connections = head["connections"]
    expected_sections = [
        {
            "name": section["name"],
            "section_index": section["section_index"],
            "source_section_index": section["source_section_index"],
            "frame_index": section["frame_index"],
            "landmark_index": section["landmark_index"],
            "owner": section["owner"],
            "center": section["center"],
            "radii": section["radii"],
            "lineage": section["lineage"],
        }
        for section in sections
    ]
    expected_connections = [
        {
            "name": connection["name"],
            "from_section_index": connection["from_section_index"],
            "to_section_index": connection["to_section_index"],
            "route": connection["route"],
            "centerline": connection["path"]["points"],
            "thickness": connection["path"]["thickness"],
        }
        for connection in connections
    ]
    route_topology = []
    for route_name, indices, tangent_axis, transverse_axes, connection_indices in SUCCESSOR_HEAD_NECK_ROUTE_TOPOLOGY:
        route_sections = [sections[index] for index in indices]
        route_topology.append({
            "name": route_name,
            "operation": "authored-head-neck-branched-route-profile-v1",
            "section_indices": list(indices),
            "section_names": [section["name"] for section in route_sections],
            "connection_names": [connections[index]["name"] for index in connection_indices],
            "tangent_axis": tangent_axis,
            "transverse_axes": list(transverse_axes),
            "owner_keys": [section["owner"] for section in route_sections],
            "station_radii": [section["radii"] for section in route_sections],
            "endpoint_cap_count": 2,
            "internal_transition_count": 0,
        })
    return {
        "profile_format": AUTHORED_HEAD_NECK_PROFILE_FORMAT,
        "operation": "authored-head-neck-branched-route-profile-v1",
        "regional_guide_format": REGIONAL_GUIDE_FORMAT,
        "provenance": head["provenance"],
        "sections_consumed": len(sections),
        "connections_consumed": len(connections),
        "sections": expected_sections,
        "connections": expected_connections,
        "route_topology": route_topology,
    }


def _expected_successor_arm_profile_metadata(guide: dict[str, Any]) -> dict[str, Any]:
    """Re-derive v9 arm-route metadata from the validated v11 guide."""

    profile = guide["controls"]["arm_profile"]
    sides = profile["sides"]
    routes: list[dict[str, Any]] = []
    for side in sides:
        side_name = side["side"]
        sections = side["sections"]
        for route_name, route_kind, route_sections in (
            (f"{side_name}-upper-arm-route", "upper-arm", sections[:3]),
            (f"{side_name}-forearm-route", "forearm", sections[2:]),
        ):
            routes.append({
                "name": route_name,
                "side": side_name,
                "route": route_kind,
                "station_names": [item["name"] for item in route_sections],
                "source_section_indices": [int(item["source_section_index"]) for item in route_sections],
                "owner_keys": [item["owner"] for item in route_sections],
                "station_count": len(route_sections),
            })
    return {
        "format": AUTHORED_ARM_PROFILE_FORMAT,
        "source": "authored_arm_profile",
        "regional_guide_format": REGIONAL_GUIDE_FORMAT,
        "operation": "authored-arm-profile-route-v1",
        "topology": "two-routes-per-side-shared-upper-arm-elbow-seam",
        "route_order": [item["name"] for item in routes],
        "routes": routes,
        "stations": [
            {
                "side": side["side"],
                "sections": [
                    {
                        "name": item["name"],
                        "section_index": int(item["section_index"]),
                        "source_section_index": int(item["source_section_index"]),
                        "owner": item["owner"],
                        "center": item["center"],
                        "radii": item["radii"],
                        "lineage": item["lineage"],
                        "consumption": item["consumption"],
                    }
                    for item in side["sections"]
                ],
            }
            for side in sides
        ],
        "elbow_ownership": "upper_arm",
    }


def _expected_successor_leg_profile_metadata(guide: dict[str, Any]) -> dict[str, Any]:
    """Re-derive v9 bilateral leg-route metadata from the validated v11 guide."""

    profile = guide["controls"]["leg_profile"]
    sides = []
    for side in profile["sides"]:
        sections = side["sections"]
        sides.append({
            "side": side["side"],
            "route": f"{side['side']}-leg",
            "route_kind": "leg-profile",
            "source_section_indices": [int(item["source_section_index"]) for item in sections],
            "station_count": len(sections),
            "owner_keys": [item["owner"] for item in sections],
            "stations": [
                {
                    "name": item["name"],
                    "section_index": int(item["section_index"]),
                    "source_section_index": int(item["source_section_index"]),
                    "owner": item["owner"],
                    "center": item["center"],
                    "frame_index": int(item["frame_index"]),
                    "landmark_index": int(item["landmark_index"]),
                    "radii": item["radii"],
                    "lineage": item["lineage"],
                    "consumption": (
                        "skin-driving; hock endpoint owned by shin station"
                        if item["name"] == "hock-endpoint"
                        else item["consumption"]
                    ),
                    "profile_provenance": item["profile_provenance"],
                    "variant_provenance": item["variant_provenance"],
                }
                for item in sections
            ],
        })
    return {
        "format": AUTHORED_LEG_PROFILE_FORMAT,
        "source": "authored_leg_profile",
        "source_format": common.PROVISIONAL_FORM_FORMAT,
        "regional_guide_format": REGIONAL_GUIDE_FORMAT,
        "operation": "authored-leg-profile-route-v1",
        "topology": "one-five-station-route-per-side-thigh-knee-shin-hock",
        "route_order": [item["route"] for item in sides],
        "route_kinds": [item["route_kind"] for item in sides],
        "section_names": list(AUTHORED_LEG_PROFILE_SECTION_NAMES),
        "owner_roles": list(AUTHORED_LEG_PROFILE_OWNER_ROLES),
        "station_count": sum(item["station_count"] for item in sides),
        "radius_count": sum(item["station_count"] for item in sides) * len(AUTHORED_LEG_PROFILE_RADIUS_AXES),
        "provenance": profile["provenance"],
        "variant_provenance": profile["variant_provenance"],
        "knee_seam": {"name": "knee", "index": 2, "owner_role": "thigh"},
        "hock_endpoint": {"name": "hock-endpoint", "index": 4, "owner_role": "shin"},
        "sides": sides,
    }


def _expected_successor_foot_profile_metadata(guide: dict[str, Any]) -> dict[str, Any]:
    """Re-derive the live v9 five-station authored foot route metadata."""

    profile = guide["controls"]["foot_profile"]
    leg_profile = guide["controls"]["leg_profile"]
    paws_by_key = {
        (tuple(item["owner"]["anchors"]), item["owner"]["role"]): item
        for item in guide["controls"]["paws"]
    }
    sides: list[dict[str, Any]] = []
    for side_index, side in enumerate(profile["sides"]):
        side_name = side["side"]
        leg_side = leg_profile["sides"][side_index]
        leg_hock = leg_side["sections"][AUTHORED_FOOT_PROFILE_HOCK_SECTION_INDEX]
        paw = paws_by_key[((side_name,), "foot")]
        chain = paw["chain"]
        masses = {item["control"]: item for item in chain["masses"]}
        midpoint = chain["midpoints"]
        station_sources = (leg_hock, None, side["sections"][0], None, side["sections"][1])
        station_values = (
            (chain["hock"]["center"], chain["hock"]["radii"]),
            (midpoint["metatarsal"]["center"], midpoint["metatarsal"]["radii"]),
            (masses["paw-pad"]["center"], masses["paw-pad"]["radii"]),
            (midpoint["pad_toe"]["center"], midpoint["pad_toe"]["radii"]),
            (masses["toe-box"]["center"], masses["toe-box"]["radii"]),
        )
        stations: list[dict[str, Any]] = []
        for index, (source, (center, radii)) in enumerate(zip(station_sources, station_values)):
            if source is leg_hock:
                lineage = {
                    "kind": "authored-leg-hock",
                    "profile": common.PROVISIONAL_FORM_LEG_PROFILE_FORMAT,
                    "source": "authored_leg_profile",
                    "radii": source["lineage"],
                    "profile_provenance": source["profile_provenance"],
                    "variant_provenance": source["variant_provenance"],
                }
            elif source is None:
                inputs = ["hock", "pad"] if index == 1 else ["pad", "toe"]
                lineage = {
                    "kind": "derived-guide-midpoint",
                    "inputs": inputs,
                    "profile_provenance": profile["provenance"],
                    "variant_provenance": profile["variant_provenance"],
                }
            else:
                lineage = {
                    "kind": "authored-foot-profile",
                    "profile": AUTHORED_FOOT_PROFILE_FORMAT,
                    "source": "authored_foot_profile",
                    "radii": source["lineage"],
                    "profile_provenance": source["profile_provenance"],
                    "variant_provenance": source["variant_provenance"],
                }
            stations.append({
                "name": ("hock", "metatarsal-midpoint", "pad", "pad-toe-midpoint", "toe")[index],
                "section_index": index,
                "source_section_index": [AUTHORED_FOOT_PROFILE_HOCK_SECTION_INDEX, 0, 0, 1, 1][index],
                "owner": leg_hock["owner"] if index == 0 else side["sections"][0]["owner"],
                "center": center,
                "volume_radii": radii,
                "lineage": lineage,
            })
        sides.append({
            "side": side_name,
            "route": f"{side_name}-foot",
            "route_kind": "foot-profile",
            "station_count": 5,
            "source_section_indices": [int(item["source_section_index"]) for item in stations],
            "owner_roles": ["shin", "foot", "foot", "foot", "foot"],
            "stations": stations,
        })
    return {
        "format": AUTHORED_FOOT_PROFILE_FORMAT,
        "source": "authored_foot_profile",
        "source_format": common.PROVISIONAL_FORM_FORMAT,
        "regional_guide_format": REGIONAL_GUIDE_FORMAT,
        "operation": "authored-foot-profile-route-v1",
        "topology": "one-five-station-hock-to-toe-route-per-side",
        "route_order": [item["route"] for item in sides],
        "route_kinds": ["foot-profile", "foot-profile"],
        "section_names": ["hock", "metatarsal-midpoint", "pad", "pad-toe-midpoint", "toe"],
        "owner_roles": ["shin", "foot", "foot", "foot", "foot"],
        "route_station_count": 10,
        "authored_station_count": 4,
        "route_volume_radius_count": 30,
        "authored_radius_count": 12,
        "provenance": profile["provenance"],
        "variant_provenance": profile["variant_provenance"],
        "sides": sides,
    }


def _expected_successor_region_metadata(
    guide: dict[str, Any],
    torso_controls: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the exact structural metadata emitted by the v9 successor.

    The values are derived from the already validated regional guide.  This is
    deliberately a complete metadata binding rather than independent length
    checks: source owner keys, ordered station names, counts, and recipe order
    all describe the guide topology consumed by the successor.
    """

    controls = guide["controls"]
    head = controls["head"]
    head_owner, neck_owner = head["owners"]
    head_neck = _expected_successor_head_neck_metadata(guide)
    arm_profile = _expected_successor_arm_profile_metadata(guide)
    leg_profile = _expected_successor_leg_profile_metadata(guide)
    foot_profile = _expected_successor_foot_profile_metadata(guide)

    limbs_by_key = {
        (tuple(item["owner"]["anchors"]), item["owner"]["role"]): item
        for item in controls["limbs"]
    }
    limb_specs = (
        ("left-leg", "left", "thigh", "shin"),
        ("right-leg", "right", "thigh", "shin"),
    )
    limb_owner_keys: list[list[dict[str, Any]]] = []
    limb_internal_transition_counts: list[int] = []
    for side in ("left", "right"):
        arm_side = next(item for item in arm_profile["stations"] if item["side"] == side)
        arm_sections = arm_side["sections"]
        for route_sections in (arm_sections[:3], arm_sections[2:]):
            limb_owner_keys.append([item["owner"] for item in route_sections])
            limb_internal_transition_counts.append(
                _profile_bend_count([item["center"] for item in route_sections], f"successor {side} authored arm route")
            )
    for chain_name, side, proximal_role, distal_role in limb_specs:
        proximal = limbs_by_key.get(((side,), proximal_role))
        distal = limbs_by_key.get(((side,), distal_role))
        if proximal is None or distal is None:
            raise SurfacePreviewPublishError(f"validated regional guide lacks {chain_name}")
        proximal_sections = {
            section["control"]: section for section in proximal["sections"]
        }
        distal_sections = {
            section["control"]: section for section in distal["sections"]
        }
        joint = proximal["joints"][0]
        if proximal_role == "upper_arm":
            points = [
                proximal_sections["pre-joint"]["points"][0],
                proximal_sections["pre-joint"]["points"][1],
                joint["mass"]["center"],
                distal_sections["proximal"]["points"][1],
                distal_sections["distal"]["points"][1],
            ]
        else:
            points = [
                proximal_sections["pre-joint"]["points"][0],
                proximal_sections["pre-joint"]["points"][1],
                joint["mass"]["center"],
                distal_sections["pre-joint"]["points"][1],
                distal["joints"][0]["mass"]["center"],
            ]
        limb_owner_keys.append([proximal["owner"]] * 3 + [distal["owner"]] * 2)
        limb_internal_transition_counts.append(
            _profile_bend_count(points, f"successor {chain_name}")
        )
    limbs = {
        "representation": "shared-guide-derived-authored-arm-and-leg-profile-routes",
        "sweeps_consumed": len(SUCCESSOR_LIMB_ORDER),
        "sweep_order": list(SUCCESSOR_LIMB_ORDER),
        "route_kinds": ["arm-profile", "arm-profile", "arm-profile", "arm-profile", "leg-profile", "leg-profile"],
        "station_counts": [len(names) for names in SUCCESSOR_LIMB_STATION_NAMES],
        "station_names": [list(names) for names in SUCCESSOR_LIMB_STATION_NAMES],
        "section_owner_keys": limb_owner_keys,
        "station_owner_keys": limb_owner_keys,
        "endpoint_cap_counts": [2] * len(SUCCESSOR_LIMB_ORDER),
        "arm_profile": arm_profile,
        "leg_profile": leg_profile,
        "foot_profile": foot_profile,
    }

    paws_by_key = {
        (tuple(item["owner"]["anchors"]), item["owner"]["role"]): item
        for item in controls["paws"]
    }
    extremity_owner_keys: list[list[dict[str, Any]]] = []
    extremity_internal_transition_counts: list[int] = []
    for side in ("left", "right"):
        hand = paws_by_key.get(((side,), "hand"))
        foot = paws_by_key.get(((side,), "foot"))
        shin = limbs_by_key.get(((side,), "shin"))
        if hand is None or foot is None or shin is None:
            raise SurfacePreviewPublishError(f"validated regional guide lacks {side} extremity controls")
        hand_mass = hand["masses"][0]
        lateral_sign = -1.0 if side == "left" else 1.0
        hand_centers = [
            [
                float(hand_mass["center"][axis])
                + offset * float(hand_mass["radii"][0]) * lateral_sign
                for axis in range(3)
            ]
            for offset in (-0.55, -0.15, 0.35, 0.78)
        ]
        foot_chain = foot["chain"]
        foot_masses = {
            item["control"]: item for item in foot_chain["masses"]
        }
        foot_centers = [
            foot_chain["hock"]["center"],
            [
                0.5 * (
                    float(foot_chain["metatarsal"]["points"][0][axis])
                    + float(foot_chain["metatarsal"]["points"][1][axis])
                )
                for axis in range(3)
            ],
            foot_masses["paw-pad"]["center"],
            [
                0.5 * (
                    float(foot_masses["paw-pad"]["center"][axis])
                    + float(foot_masses["toe-box"]["center"][axis])
                )
                for axis in range(3)
            ],
            foot_masses["toe-box"]["center"],
        ]
        extremity_owner_keys.extend([
            [hand["owner"], hand["owner"]],
            [hand["owner"]] * 4,
            [shin["owner"]] + [foot["owner"]] * 4,
        ])
        extremity_internal_transition_counts.extend([
            0,
            _profile_bend_count(hand_centers, f"successor {side}-hand-paw"),
            _profile_bend_count(foot_centers, f"successor {side}-foot"),
        ])
    extremities = {
        "representation": "shared-guide-derived-hand-and-digitigrade-foot-profile-sweeps",
        "sweeps_consumed": len(SUCCESSOR_EXTREMITY_ORDER),
        "sweep_order": list(SUCCESSOR_EXTREMITY_ORDER),
        "sweep_kinds": list(SUCCESSOR_EXTREMITY_KINDS),
        "station_counts": [len(names) for names in SUCCESSOR_EXTREMITY_STATION_NAMES],
        "station_names": [list(names) for names in SUCCESSOR_EXTREMITY_STATION_NAMES],
        "section_owner_keys": extremity_owner_keys,
        "endpoint_cap_counts": [2] * len(SUCCESSOR_EXTREMITY_ORDER),
        "internal_transition_counts": extremity_internal_transition_counts,
    }

    tails = controls["tails"]
    tails_by_role = {item["owner"]["role"]: item for item in tails}
    root = tails_by_role.get("tail_root")
    tip = tails_by_role.get("tail_tip")
    if root is None or tip is None:
        raise SurfacePreviewPublishError("validated regional guide lacks the ordered tail controls")
    tail_owner_keys = [root["owner"]] * 3 + [tip["owner"]] * 3
    tail = {
        "representation": "shared-guide-derived-profile-sweep-elements",
        "elements_consumed": len(SUCCESSOR_TAIL_ORDER),
        "element_order": list(SUCCESSOR_TAIL_ORDER),
        "element_kinds": list(SUCCESSOR_TAIL_KINDS),
        "section_counts": [len(names) for names in SUCCESSOR_TAIL_SECTION_NAMES],
        "section_names": [list(names) for names in SUCCESSOR_TAIL_SECTION_NAMES],
        "owner_keys": tail_owner_keys,
        "endpoint_cap_counts": [2] * len(SUCCESSOR_TAIL_ORDER),
        "internal_transition_counts": [0] * len(SUCCESSOR_TAIL_ORDER),
    }

    source_owner_keys: list[dict[str, Any]] = []
    for section_owners in limbs["section_owner_keys"]:
        sweep_sources: list[dict[str, Any]] = []
        for section_owner in section_owners:
            if section_owner not in sweep_sources:
                sweep_sources.append(section_owner)
        source_owner_keys.extend(sweep_sources)
    extremity_source_owner_keys = []
    for side in ("left", "right"):
        hand = paws_by_key[((side,), "hand")]["owner"]
        foot = paws_by_key[((side,), "foot")]["owner"]
        shin = limbs_by_key[((side,), "shin")]["owner"]
        extremity_source_owner_keys.extend([hand, hand, shin, foot])

    metrics_region = {
        "regional_guide_format": REGIONAL_GUIDE_FORMAT,
        "torso_representation": "rounded-superellipse-axial-profile-sweep-v1",
        "torso_profile_exponent": 4.0,
        "torso_sections_consumed": len(torso_controls),
        "torso_section_names": list(AUTHORED_TORSO_PROFILE_SECTION_NAMES),
        "torso_section_owner_keys": [item["owner"] for item in torso_controls],
        "torso_section_controls": torso_controls,
        "shoulder_representation": "authored-five-section-frame-aware-profile-sweeps",
        "shoulder_sweeps_consumed": 2,
        "shoulder_sweep_order": ["left-shoulder-envelope", "right-shoulder-envelope"],
        "shoulder_sweep_section_counts": [5, 5],
        "shoulder_sweep_section_names": [
            ["torso-interior", "torso-boundary", "authored-shoulder", "upper-arm-socket", "upper-arm-midpoint"],
            ["torso-interior", "torso-boundary", "authored-shoulder", "upper-arm-socket", "upper-arm-midpoint"],
        ],
        "shoulder_sweep_section_owner_keys": [
            [
                controls["shoulder_frame"]["owners"]["torso"],
                controls["shoulder_frame"]["owners"]["torso"],
                controls["shoulder_frame"]["owners"][f"{side}_upper_arm"],
                controls["shoulder_frame"]["owners"][f"{side}_upper_arm"],
                controls["shoulder_frame"]["owners"][f"{side}_upper_arm"],
            ]
            for side in ("left", "right")
        ],
        "shoulder_sweep_controls": None,
        "head_neck": head_neck,
        "arm_profile": arm_profile,
        "limb_representation": limbs["representation"],
        "limb_sweeps_consumed": limbs["sweeps_consumed"],
        "limb_sweep_order": limbs["sweep_order"],
        "limb_sweep_route_kinds": limbs["route_kinds"],
        "limb_sweep_station_counts": limbs["station_counts"],
        "limb_sweep_station_names": limbs["station_names"],
        "limb_sweep_section_owner_keys": limbs["section_owner_keys"],
        "limb_sweep_station_owner_keys": limbs["station_owner_keys"],
        "limb_sweep_endpoint_cap_counts": limbs["endpoint_cap_counts"],
        "limb_sweep_internal_transition_counts": limb_internal_transition_counts,
        "limb_source_owner_keys": source_owner_keys,
        "leg_profile": leg_profile,
        "foot_profile": foot_profile,
        "extremity_representation": extremities["representation"],
        "extremity_sweeps_consumed": extremities["sweeps_consumed"],
        "extremity_sweep_order": extremities["sweep_order"],
        "extremity_sweep_kinds": extremities["sweep_kinds"],
        "extremity_sweep_station_counts": extremities["station_counts"],
        "extremity_sweep_station_names": extremities["station_names"],
        "extremity_sweep_section_owner_keys": extremities["section_owner_keys"],
        "extremity_sweep_endpoint_cap_counts": extremities["endpoint_cap_counts"],
        "extremity_sweep_internal_transition_counts": extremities["internal_transition_counts"],
        "extremity_source_owner_keys": extremity_source_owner_keys,
        "tail_representation": tail["representation"],
        "tail_elements_consumed": tail["elements_consumed"],
        "tail_element_order": tail["element_order"],
        "tail_element_kinds": tail["element_kinds"],
        "tail_element_section_counts": tail["section_counts"],
        "tail_element_section_names": tail["section_names"],
        "tail_element_owner_keys": tail["owner_keys"],
        "tail_element_endpoint_cap_counts": tail["endpoint_cap_counts"],
        "tail_element_internal_transition_counts": tail["internal_transition_counts"],
        "tail_source_owner_keys": [root["owner"], tip["owner"]],
        "tail_element_controls": None,
        "tail_tip_shared_endpoint": None,
        "replaced_baseline_field_count": 48,
        "replaced_baseline_recipes": list(SUCCESSOR_REPLACED_BASELINE_RECIPES),
    }
    return {
        "torso": {
            "representation": "rounded-superellipse-axial-profile-sweep-v1",
            "regional_guide_format": REGIONAL_GUIDE_FORMAT,
            "superellipse_exponent": 4.0,
            "sections_consumed": len(torso_controls),
            "section_names": list(AUTHORED_TORSO_PROFILE_SECTION_NAMES),
            "section_controls": torso_controls,
        },
        "shoulders": {
            "representation": "authored-five-section-frame-aware-profile-sweeps",
            "sweeps_consumed": 2,
            "sweep_order": ["left-shoulder-envelope", "right-shoulder-envelope"],
            "section_counts": [5, 5],
            "section_names": metrics_region["shoulder_sweep_section_names"],
        },
        "head_neck": head_neck,
        "limbs": limbs,
        "extremities": extremities,
        "tail": tail,
        "metrics_region": metrics_region,
    }


def _validate_successor_tail_controls(
    tail: dict[str, Any],
    guide: dict[str, Any],
    expected_tail: dict[str, Any],
) -> None:
    controls = tail.get("controls")
    if not isinstance(controls, list) or len(controls) != len(SUCCESSOR_TAIL_ORDER):
        raise SurfacePreviewPublishError("successor tail controls are not the exact six-element inventory")
    for index, (control, name, kind, owner, names) in enumerate(
        zip(
            controls,
            SUCCESSOR_TAIL_ORDER,
            SUCCESSOR_TAIL_KINDS,
            expected_tail["owner_keys"],
            SUCCESSOR_TAIL_SECTION_NAMES,
        )
    ):
        where = f"successor tail.controls[{index}]"
        if not isinstance(control, dict) or set(control) != {"name", "kind", "owner", "sections", "endpoint_caps"}:
            raise SurfacePreviewPublishError(f"{where} has an invalid generated shape")
        if control["name"] != name or control["kind"] != kind or control["owner"] != owner:
            raise SurfacePreviewPublishError(f"{where} identity does not match the validated guide")
        sections = control["sections"]
        if not isinstance(sections, list) or len(sections) != len(names):
            raise SurfacePreviewPublishError(f"{where}.sections has the wrong generated count")
        for section_index, section in enumerate(sections):
            section_where = f"{where}.sections[{section_index}]"
            if not isinstance(section, dict) or set(section) != {
                "name", "center", "tangent", "transverse_axes", "transverse_radii", "path_length"
            }:
                raise SurfacePreviewPublishError(f"{section_where} has an invalid generated shape")
            if section["name"] != names[section_index]:
                raise SurfacePreviewPublishError(f"{section_where}.name is not canonical")
            _point(section["center"], f"{section_where}.center")
            _point(section["tangent"], f"{section_where}.tangent")
            axes = section["transverse_axes"]
            if not isinstance(axes, list) or len(axes) != 2:
                raise SurfacePreviewPublishError(f"{section_where}.transverse_axes is invalid")
            for axis_index, axis in enumerate(axes):
                _point(axis, f"{section_where}.transverse_axes[{axis_index}]")
            radii = section["transverse_radii"]
            if not isinstance(radii, list) or len(radii) != 2 or any(
                _finite_number(value, f"{section_where}.transverse_radii") <= 0.0 for value in radii
            ):
                raise SurfacePreviewPublishError(f"{section_where}.transverse_radii is invalid")
            _finite_number(section["path_length"], f"{section_where}.path_length")
        caps = control["endpoint_caps"]
        if not isinstance(caps, list) or len(caps) != 2:
            raise SurfacePreviewPublishError(f"{where}.endpoint_caps must contain two generated caps")
        for cap_index, cap in enumerate(caps):
            cap_where = f"{where}.endpoint_caps[{cap_index}]"
            if not isinstance(cap, dict) or set(cap) != {
                "side", "center", "outward_tangent", "transverse_axes", "transverse_radii", "axial_radius"
            }:
                raise SurfacePreviewPublishError(f"{cap_where} has an invalid generated shape")
            if cap["side"] not in {"start", "end"}:
                raise SurfacePreviewPublishError(f"{cap_where}.side is invalid")
            _point(cap["center"], f"{cap_where}.center")
            _point(cap["outward_tangent"], f"{cap_where}.outward_tangent")
            if not isinstance(cap["transverse_axes"], list) or len(cap["transverse_axes"]) != 2:
                raise SurfacePreviewPublishError(f"{cap_where}.transverse_axes is invalid")
            for axis_index, axis in enumerate(cap["transverse_axes"]):
                _point(axis, f"{cap_where}.transverse_axes[{axis_index}]")
            radii = cap["transverse_radii"]
            if not isinstance(radii, list) or len(radii) != 2 or any(
                _finite_number(value, f"{cap_where}.transverse_radii") <= 0.0 for value in radii
            ):
                raise SurfacePreviewPublishError(f"{cap_where}.transverse_radii is invalid")
            if _finite_number(cap["axial_radius"], f"{cap_where}.axial_radius") <= 0.0:
                raise SurfacePreviewPublishError(f"{cap_where}.axial_radius is invalid")

    tails = {item["owner"]["role"]: item for item in guide["controls"]["tails"]}
    root = tails["tail_root"]
    tip = tails["tail_tip"]

    def check_path(element_index: int, path: dict[str, Any], where: str) -> None:
        for section, expected_center, expected_radius in zip(
            controls[element_index]["sections"],
            path["points"],
            path["thickness"],
        ):
            if section["center"] != expected_center or section["transverse_radii"] != [expected_radius, expected_radius]:
                raise SurfacePreviewPublishError(f"{where} does not retain the exact validated guide path")

    check_path(0, root["centerline"], "successor tail root source")
    check_path(3, tip["centerline"], "successor tail tip source")
    check_path(4, tip["sections"][0], "successor tail tip extension")
    root_attachment = root["sections"][0]
    if controls[1]["sections"][-1]["center"] != root_attachment["points"][-1] or controls[1]["sections"][-1]["transverse_radii"] != [root_attachment["thickness"][-1]] * 2:
        raise SurfacePreviewPublishError("successor tail root attachment loses its exact guide endpoint")
    root_collar = root["masses"][0]
    root_collar_sections = controls[2]["sections"]
    if root_collar_sections[len(root_collar_sections) // 2]["center"] != root_collar["center"] or root_collar_sections[len(root_collar_sections) // 2]["transverse_radii"] != root_collar["radii"][:2]:
        raise SurfacePreviewPublishError("successor tail root collar loses its exact guide control")
    tip_cap = tip["masses"][0]
    tip_cap_sections = controls[5]["sections"]
    if tip_cap_sections[len(tip_cap_sections) // 2]["center"] != tip_cap["center"] or tip_cap_sections[len(tip_cap_sections) // 2]["transverse_radii"] != tip_cap["radii"][:2]:
        raise SurfacePreviewPublishError("successor tail tip cap loses its exact guide control")
    endpoint = tail.get("tip_shared_endpoint")
    if not isinstance(endpoint, dict) or set(endpoint) != {"point", "source_end_profile", "extension_start_profile"}:
        raise SurfacePreviewPublishError("successor tail tip shared endpoint has an invalid generated shape")
    if endpoint["point"] != tip["sections"][0]["points"][0]:
        raise SurfacePreviewPublishError("successor tail tip shared endpoint does not bind the guide")
    expected_source_profile = [tip["centerline"]["thickness"][-1]] * 2
    expected_extension_profile = [tip["sections"][0]["thickness"][0]] * 2
    if endpoint["source_end_profile"] != expected_source_profile or endpoint["extension_start_profile"] != expected_extension_profile:
        raise SurfacePreviewPublishError("successor tail tip profiles do not bind the guide")


def _validate_successor_sidecar(
    path: Path,
    *,
    variant_id: str,
    profile_id: str,
    source_variant_sha256: str,
    source: dict[str, Any],
    frame: dict[str, Any],
    metrics: dict[str, Any],
    producer_payload: dict[str, Any],
    baseline_guide: dict[str, Any],
) -> dict[str, Any]:
    sidecar = _read_json(path, MAX_METRICS_BYTES, "successor.json")
    _finite_json(sidecar, "successor.json")
    _bounded_json(sidecar, "successor.json")
    expected_fields = {
        "format", "variant_id", "profile_id", "source_variant_sha256", "consumer_id", "successor_region_id",
        "capture", "torso", "shoulders", "head_neck", "limbs", "extremities", "tail",
        "temporary_bridge", "replaced_baseline_recipes",
    }
    if set(sidecar) != expected_fields:
        raise SurfacePreviewPublishError("successor sidecar has unknown or missing fields")
    if (
        sidecar.get("format") != SUCCESSOR_PREVIEW_FORMAT
        or sidecar.get("variant_id") != variant_id
        or sidecar.get("profile_id") != profile_id
        or sidecar.get("source_variant_sha256") != source_variant_sha256
        or sidecar.get("consumer_id") != SUCCESSOR_CONSUMER_ID
        or sidecar.get("successor_region_id") != SUCCESSOR_REGION_ID
    ):
        raise SurfacePreviewPublishError("successor sidecar identity is invalid")

    producer_source = producer_payload.get("source")
    producer_scale = producer_payload.get("reference_scale")
    if (
        not isinstance(producer_source, dict)
        or not isinstance(producer_scale, dict)
        or source.get("format") != common.PROVISIONAL_FORM_FORMAT
        or source.get("document") != producer_source.get("document")
        or source.get("namespace") != producer_source.get("namespace")
        or source.get("resource_profile_id") != producer_source.get("resource_profile_id")
        or source.get("reference_scale") != producer_scale
    ):
        raise SurfacePreviewPublishError("successor sidecar source argument does not bind producer identity")

    capture = sidecar.get("capture")
    if not isinstance(capture, dict) or set(capture) != set(frame) or capture != frame:
        raise SurfacePreviewPublishError("successor sidecar capture framing does not match baseline")

    torso = sidecar.get("torso")
    if not isinstance(torso, dict) or set(torso) != {"representation", "regional_guide_format", "superellipse_exponent", "sections_consumed", "section_names", "section_controls"}:
        raise SurfacePreviewPublishError("successor torso representation metadata is missing")
    profile_binding = _validate_authored_torso_profile(producer_payload)["variants"].get(variant_id)
    if profile_binding is None:
        raise SurfacePreviewPublishError("successor torso representation cannot bind producer variant")
    expected_torso_controls = _expected_successor_torso_controls(producer_payload, variant_id, profile_binding)
    guide_sections = baseline_guide.get("controls", {}).get("torso_cage", {}).get("sections")
    if not isinstance(guide_sections, list) or len(guide_sections) != len(expected_torso_controls):
        raise SurfacePreviewPublishError("successor torso cannot bind the validated baseline guide sections")
    guide_torso_controls = [
        {
            "name": section["name"],
            "owner": section["owner"],
            "center": section["center"],
            "axial_position": section["center"][1],
            "lateral_radius": section["lateral_radius"],
            "anterior_radius": section["anterior_radius"],
            "posterior_radius": section["posterior_radius"],
        }
        for section in guide_sections
    ]
    if guide_torso_controls != expected_torso_controls:
        raise SurfacePreviewPublishError("successor torso claims do not match the validated baseline regional guide")
    expected_metadata = _expected_successor_region_metadata(
        baseline_guide, expected_torso_controls
    )
    for key in ("torso", "shoulders", "head_neck", "limbs", "extremities"):
        if sidecar.get(key) != expected_metadata[key]:
            raise SurfacePreviewPublishError(
                f"successor {key.replace('_', '/')} metadata does not match the validated guide"
            )
    tail = sidecar.get("tail")
    expected_tail = expected_metadata["tail"]
    if not isinstance(tail, dict) or set(tail) != set(expected_tail) | {"controls", "tip_shared_endpoint"}:
        raise SurfacePreviewPublishError("successor tail representation metadata is missing or incomplete")
    if any(tail.get(key) != value for key, value in expected_tail.items()):
        raise SurfacePreviewPublishError("successor tail topology metadata does not match the validated guide")
    _validate_successor_tail_controls(tail, baseline_guide, expected_tail)

    bridge = sidecar.get("temporary_bridge")
    if not isinstance(bridge, dict) or set(bridge) != {"enabled", "consumer", "regions", "field_count", "retained_recipes"}:
        raise SurfacePreviewPublishError("successor temporary bridge metadata is missing")
    if (
        bridge.get("enabled") is not True
        or bridge.get("consumer") != "baseline-analytic-fields"
        or bridge.get("regions") != ["thigh-root-connectors", "hip-transitions"]
        or bridge.get("field_count") != 4
        or bridge.get("retained_recipes") != list(SUCCESSOR_RETAINED_BRIDGE_RECIPES)
    ):
        raise SurfacePreviewPublishError(
            "successor temporary bridge must contain only two thigh-root and two hip fields"
        )
    retained = bridge["retained_recipes"]
    if any(recipe in SUCCESSOR_REPLACED_EXTREMITY_AND_TAIL_RECIPES for recipe in retained):
        raise SurfacePreviewPublishError("successor temporary bridge retains baseline paw, foot, or tail recipes")

    replaced = sidecar.get("replaced_baseline_recipes")
    if not isinstance(replaced, list) or not all(isinstance(recipe, str) and recipe for recipe in replaced):
        raise SurfacePreviewPublishError("successor replaced-baseline recipe metadata is invalid")
    if replaced != list(SUCCESSOR_REPLACED_BASELINE_RECIPES):
        raise SurfacePreviewPublishError("successor sidecar does not contain the exact replaced-baseline recipe inventory")
    if any(recipe in SUCCESSOR_REPLACED_EXTREMITY_AND_TAIL_RECIPES for recipe in retained):
        raise SurfacePreviewPublishError("successor sidecar retains a replaced baseline recipe")

    if metrics.get("consumer_id") != SUCCESSOR_CONSUMER_ID or metrics.get("successor_region_id") != SUCCESSOR_REGION_ID:
        raise SurfacePreviewPublishError("successor metrics identity does not match sidecar")
    metrics_region = metrics.get("successor_region")
    if not isinstance(metrics_region, dict) or not metrics_region:
        raise SurfacePreviewPublishError("successor metrics lack region representation metadata")
    expected_metrics_region = expected_metadata["metrics_region"]
    if set(metrics_region) != set(expected_metrics_region):
        raise SurfacePreviewPublishError(
            "successor metrics region has unknown or missing generated metadata"
        )
    dynamic_metrics_keys = {
        "shoulder_sweep_controls",
        "tail_element_controls",
        "tail_tip_shared_endpoint",
    }
    for key, expected in expected_metrics_region.items():
        if key in dynamic_metrics_keys:
            continue
        if metrics_region.get(key) != expected:
            raise SurfacePreviewPublishError(
                f"successor metrics region {key} does not match the validated guide"
            )
    if torso.get("section_controls") != metrics_region.get("torso_section_controls"):
        raise SurfacePreviewPublishError(
            "successor metrics torso controls disagree with the sidecar"
        )

    producer_variants = producer_payload.get("variants")
    producer_landmarks = producer_payload.get("authored_landmarks")
    producer_dimensions = producer_payload.get("authored_dimensions")
    producer_scale = producer_payload.get("reference_scale")
    if (
        not isinstance(producer_variants, list)
        or not isinstance(producer_landmarks, list)
        or not isinstance(producer_dimensions, list)
        or not isinstance(producer_scale, dict)
        or type(producer_scale.get("squared_length")) is not int
        or producer_scale["squared_length"] <= 0
    ):
        raise SurfacePreviewPublishError(
            "successor shoulder metrics cannot bind v10 producer controls"
        )
    producer_variant = next(
        (
            item
            for item in producer_variants
            if isinstance(item, dict) and item.get("id") == variant_id
        ),
        None,
    )
    if not isinstance(producer_variant, dict) or not isinstance(
        producer_variant.get("descriptors"), list
    ):
        raise SurfacePreviewPublishError(
            "successor shoulder metrics cannot bind their producer variant"
        )
    descriptors = producer_variant["descriptors"]
    torso_descriptors = [
        item
        for item in descriptors
        if isinstance(item, dict)
        and isinstance(item.get("address"), dict)
        and item["address"].get("role") == "torso"
        and item["address"].get("anchors") == []
    ]
    if len(torso_descriptors) != 1:
        raise SurfacePreviewPublishError(
            "successor shoulder metrics have no unique torso producer owner"
        )
    torso_owner = torso_descriptors[0]["address"]
    controls = metrics_region.get("shoulder_sweep_controls")
    owner_keys = metrics_region.get("shoulder_sweep_section_owner_keys")
    if not isinstance(controls, list) or len(controls) != 2:
        raise SurfacePreviewPublishError(
            "successor shoulder metrics lack the two authored control records"
        )
    if not isinstance(owner_keys, list) or len(owner_keys) != 2:
        raise SurfacePreviewPublishError(
            "successor shoulder metrics lack section ownership"
        )
    reference_scale = math.sqrt(float(producer_scale["squared_length"]))
    depth_factor = {
        "neutral-v0": 1_000,
        "broad-soft-v0": 1_150,
        "lean-readable-v0": 800,
        "depth-forward-v0": 1_000,
    }[variant_id]
    for index, side_name in enumerate(("left", "right")):
        where = f"successor shoulder metrics[{side_name}]"
        upper_arms = [
            item
            for item in descriptors
            if isinstance(item, dict)
            and isinstance(item.get("address"), dict)
            and item["address"].get("role") == "upper_arm"
            and item["address"].get("anchors") == [side_name]
        ]
        if len(upper_arms) != 1:
            raise SurfacePreviewPublishError(f"{where} has no unique upper-arm producer owner")
        upper_arm = upper_arms[0]
        upper_owner = upper_arm["address"]
        reference_point = upper_arm.get("reference_point")
        if not isinstance(reference_point, list) or len(reference_point) != 3:
            raise SurfacePreviewPublishError(f"{where} producer reference point is invalid")
        landmarks = [
            item
            for item in producer_landmarks
            if isinstance(item, dict)
            and item.get("owner") == upper_owner
            and item.get("role") in {"form_axilla", "form_shoulder_peak"}
        ]
        dimensions = [
            item
            for item in producer_dimensions
            if isinstance(item, dict)
            and item.get("owner") == upper_owner
            and item.get("role") == "form_shoulder_depth_radius"
        ]
        if len(landmarks) != 2 or len(dimensions) != 1:
            raise SurfacePreviewPublishError(f"{where} producer controls are incomplete")
        landmark_by_role = {item["role"]: item for item in landmarks}
        peak_position = landmark_by_role["form_shoulder_peak"].get("position")
        axilla_position = landmark_by_role["form_axilla"].get("position")
        depth_value = dimensions[0].get("value_permille")
        if (
            not isinstance(peak_position, list)
            or len(peak_position) != 3
            or not isinstance(axilla_position, list)
            or len(axilla_position) != 3
            or type(depth_value) is not int
            or depth_value <= 0
        ):
            raise SurfacePreviewPublishError(f"{where} producer control values are invalid")
        peak_anchor = [
            (float(reference_point[axis]) + float(peak_position[axis]))
            / reference_scale
            for axis in range(3)
        ]
        axilla_anchor = [
            (float(reference_point[axis]) + float(axilla_position[axis]))
            / reference_scale
            for axis in range(3)
        ]
        expected_center = [
            0.5 * (peak_anchor[axis] + axilla_anchor[axis])
            for axis in range(3)
        ]
        expected_vertical = 0.5 * (peak_anchor[1] - axilla_anchor[1])
        expected_depth = (depth_value * depth_factor // 1_000) / 1_000.0
        control = controls[index]
        if not isinstance(control, dict) or set(control) != {
            "side", "authored_center", "vertical_radius", "depth_radius"
        }:
            raise SurfacePreviewPublishError(f"{where} control record is invalid")
        center = control.get("authored_center")
        parsed_center = (
            [
                _finite_number(value, f"{where}.authored_center[{axis}]")
                for axis, value in enumerate(center)
            ]
            if isinstance(center, list) and len(center) == 3
            else None
        )
        actual_vertical = _finite_number(
            control.get("vertical_radius"), f"{where}.vertical_radius"
        )
        actual_depth = _finite_number(
            control.get("depth_radius"), f"{where}.depth_radius"
        )
        if (
            control.get("side") != side_name
            or parsed_center is None
            or any(
                not math.isclose(float(actual), expected, rel_tol=0.0, abs_tol=1.0e-12)
                for actual, expected in zip(parsed_center or (), expected_center)
            )
            or not math.isclose(
                actual_vertical,
                expected_vertical,
                rel_tol=0.0,
                abs_tol=1.0e-12,
            )
            or not math.isclose(
                actual_depth,
                expected_depth,
                rel_tol=0.0,
                abs_tol=1.0e-12,
            )
        ):
            raise SurfacePreviewPublishError(
                f"{where} does not match the exact producer controls"
            )
        if owner_keys[index] != [torso_owner, torso_owner, upper_owner, upper_owner, upper_owner]:
            raise SurfacePreviewPublishError(
                f"{where} section ownership is not torso/upper-arm source-owned"
            )
    if metrics_region["shoulder_sweep_section_owner_keys"] != expected_metrics_region["shoulder_sweep_section_owner_keys"]:
        raise SurfacePreviewPublishError("successor shoulder metrics ownership does not match the validated guide")
    if metrics_region.get("tail_element_controls") != tail["controls"] or metrics_region.get("tail_tip_shared_endpoint") != tail["tip_shared_endpoint"]:
        raise SurfacePreviewPublishError("successor tail metrics disagree with the sidecar")
    if metrics_region.get("replaced_baseline_recipes") != replaced or metrics.get("temporary_bridge") != bridge:
        raise SurfacePreviewPublishError("successor metrics disagree with sidecar checkpoint metadata")
    return sidecar


def _validate_successor_semantic_sidecar(
    path: Path,
    *,
    variant_id: str,
    source_format: str,
    source_variant_sha256: str,
    surface_sha256: str,
    ply_metrics: dict[str, Any],
    descriptor_owners: list[dict[str, Any]],
) -> dict[str, Any]:
    """Validate source-only per-vertex winners at the shared sidecar boundary.

    The publication process has the PLY vertex count and producer descriptor
    ownership, but it does not re-run the successor field evaluator.  It can
    therefore prove count, identity, source ownership, and inventory/hash
    binding without claiming to recompute geometric winner selection.
    """

    sidecar = _read_json(path, MAX_SEMANTIC_SIDECAR_BYTES, "semantic.json")
    expected_fields = {
        "format", "source_format", "variant_id", "source_variant_sha256",
        "surface_sha256", "vertex_count", "source_node_labels", "attribution",
    }
    if not isinstance(sidecar, dict) or set(sidecar) != expected_fields:
        raise SurfacePreviewPublishError("successor semantic sidecar has unknown or missing fields")
    if (
        sidecar.get("format") != SEMANTIC_SIDECAR_FORMAT
        or sidecar.get("source_format") != source_format
        or sidecar.get("variant_id") != variant_id
        or sidecar.get("source_variant_sha256") != source_variant_sha256
        or sidecar.get("surface_sha256") != surface_sha256
        or sidecar.get("attribution")
        != "every recipe component resolves to its source descriptor owner; no synthetic node identity is emitted"
    ):
        raise SurfacePreviewPublishError("successor semantic sidecar identity or boundary is invalid")
    vertex_count = sidecar.get("vertex_count")
    if (
        type(vertex_count) is not int
        or not 0 < vertex_count <= MAX_SUCCESSOR_PLY_VERTICES
        or vertex_count != ply_metrics.get("vertex_count")
    ):
        raise SurfacePreviewPublishError("successor semantic sidecar vertex_count does not match the validated PLY")
    labels = sidecar.get("source_node_labels")
    if not isinstance(labels, list) or len(labels) != vertex_count:
        raise SurfacePreviewPublishError("successor semantic sidecar labels do not match the validated PLY vertex count")
    allowed = {_address_sort_key(owner) for owner in descriptor_owners}
    if len(allowed) != len(descriptor_owners):
        raise SurfacePreviewPublishError("successor producer descriptor ownership is not unique")
    for index, label in enumerate(labels):
        parsed = _validate_address(label, f"semantic.json.source_node_labels[{index}]")
        if _address_sort_key(parsed) not in allowed:
            raise SurfacePreviewPublishError(
                "successor semantic sidecar label is not a producer source AddressKey"
            )
    return sidecar


def _validate_successor_bundle(
    bundle: Path,
    expected_source_sha256: str,
    producer_payload: dict[str, Any],
    baseline_manifest: dict[str, Any],
    baseline_guides: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Validate the successor v9 publication boundary against baseline v3."""

    try:
        bundle_info = bundle.lstat()
    except OSError as exc:
        raise SurfacePreviewPublishError("successor bundle root is unavailable") from exc
    if stat.S_ISLNK(bundle_info.st_mode) or not stat.S_ISDIR(bundle_info.st_mode):
        raise SurfacePreviewPublishError("successor bundle root must be a real non-symlink directory")
    manifest = _read_json(bundle / SUCCESSOR_MANIFEST_NAME, MAX_MANIFEST_BYTES, SUCCESSOR_MANIFEST_NAME)
    _finite_json(manifest, SUCCESSOR_MANIFEST_NAME)
    expected_fields = {"format", "status", "consumer_id", "source_format", "source", "shared_render_bounds", "canvas", "layout", "projections", "generator", "variants"}
    if set(manifest) != expected_fields or manifest.get("format") != SUCCESSOR_PREVIEW_FORMAT or manifest.get("status") != "success":
        raise SurfacePreviewPublishError("successor bundle has unsupported format, status, or fields")
    if manifest.get("consumer_id") != SUCCESSOR_CONSUMER_ID or manifest.get("source_format") != common.PROVISIONAL_FORM_FORMAT:
        raise SurfacePreviewPublishError("successor bundle identity or source format is invalid")

    producer_source = producer_payload.get("source")
    producer_reference_scale = producer_payload.get("reference_scale")
    if not isinstance(producer_source, dict) or not isinstance(producer_reference_scale, dict):
        raise SurfacePreviewPublishError("successor bundle cannot bind producer provenance")
    source = manifest.get("source")
    expected_source = {
        "format": common.PROVISIONAL_FORM_FORMAT,
        "sha256": expected_source_sha256,
        "document": producer_source.get("document"),
        "namespace": producer_source.get("namespace"),
        "resource_profile_id": producer_source.get("resource_profile_id"),
        "reference_scale": producer_reference_scale,
    }
    if not isinstance(source, dict) or source != expected_source:
        raise SurfacePreviewPublishError("successor source hash or provenance does not match producer output")
    if source.get("resource_profile_id") != common.PROVISIONAL_FORM_RESOURCE_PROFILE:
        raise SurfacePreviewPublishError("successor source resource profile is invalid")
    if not isinstance(source.get("sha256"), str) or len(source["sha256"]) != 64 or any(character not in "0123456789abcdef" for character in source["sha256"]):
        raise SurfacePreviewPublishError("successor source.sha256 is invalid")
    _validate_reference_scale(source.get("reference_scale"), "successor source.reference_scale")

    frame_keys = ("canvas", "projections", "layout", "shared_render_bounds")
    frame = {key: manifest.get(key) for key in frame_keys}
    if any(manifest.get(key) != baseline_manifest.get(key) for key in frame_keys):
        raise SurfacePreviewPublishError("successor capture framing does not exactly match the validated baseline")

    baseline_generator = baseline_manifest.get("generator")
    if not isinstance(baseline_generator, dict) or type(baseline_generator.get("padding")) not in {int, float}:
        raise SurfacePreviewPublishError("validated baseline generator padding is unavailable")
    baseline_capture_padding = baseline_generator["padding"]
    if not math.isfinite(float(baseline_capture_padding)) or not 0.0 <= baseline_capture_padding <= 100.0:
        raise SurfacePreviewPublishError("validated baseline generator padding is out of bounds")

    generator = manifest.get("generator")
    if not isinstance(generator, dict) or set(generator) != {"samples_per_axis", "padding", "capture_padding", "smooth_k", "consumer_boundary", "production_status", "component_visualization"}:
        raise SurfacePreviewPublishError("successor generator configuration has unknown or missing fields")
    _finite_json(generator, "successor generator")
    _bounded_json(generator, "successor generator")
    if generator.get("component_visualization") != EXPECTED_COMPONENT_VISUALIZATION:
        raise SurfacePreviewPublishError("successor generator.component_visualization is not the exact consumed-component visualization")
    try:
        generator_metadata = common._metadata(generator, "successor generator", max_len=8192)
    except ValidationError as exc:
        raise SurfacePreviewPublishError(str(exc)) from exc
    if type(generator["samples_per_axis"]) is not int or not 20 <= generator["samples_per_axis"] <= 96:
        raise SurfacePreviewPublishError("successor generator.samples_per_axis is out of bounds")
    if type(generator["padding"]) not in {int, float} or not 0.0 <= generator["padding"] <= 100.0:
        raise SurfacePreviewPublishError("successor generator.padding is out of bounds")
    if type(generator["capture_padding"]) not in {int, float} or not math.isfinite(float(generator["capture_padding"])) or not 0.0 <= generator["capture_padding"] <= 100.0:
        raise SurfacePreviewPublishError("successor generator.capture_padding is out of bounds")
    if generator["capture_padding"] != baseline_capture_padding:
        raise SurfacePreviewPublishError("successor capture_padding does not match validated baseline generator padding")
    if type(generator["smooth_k"]) not in {int, float} or not 0.0 < generator["smooth_k"] <= 100.0:
        raise SurfacePreviewPublishError("successor generator.smooth_k is out of bounds")
    if (
        generator.get("production_status") != "disposable exploratory proof"
        or generator.get("consumer_boundary")
        != "successor torso/shoulder/head/neck, authored arm and leg profile routes, bilateral hands, digitigrade feet, and tail; baseline temporary bridge for thigh-root/hip connectors"
    ):
        raise SurfacePreviewPublishError("successor generator boundary metadata is invalid")

    variants = manifest.get("variants")
    if not isinstance(variants, list) or len(variants) != len(EXPECTED_VARIANTS) or any(not isinstance(item, dict) for item in variants) or {item.get("id") for item in variants} != set(EXPECTED_VARIANTS) or len({item.get("id") for item in variants}) != len(EXPECTED_VARIANTS):
        raise SurfacePreviewPublishError("successor variants must contain the exact canonical variant ids")
    producer_variants = producer_payload.get("variants")
    profile_binding = _validate_authored_torso_profile(producer_payload)
    if not isinstance(baseline_guides, dict) or set(baseline_guides) != set(EXPECTED_VARIANTS) or any(
        not isinstance(guide, dict) for guide in baseline_guides.values()
    ):
        raise SurfacePreviewPublishError("successor cannot bind the exact validated baseline guide set")
    producer_by_id = {item.get("id"): item for item in producer_variants} if isinstance(producer_variants, list) and all(isinstance(item, dict) for item in producer_variants) else {}
    if not isinstance(producer_variants, list) or len(producer_by_id) != len(EXPECTED_VARIANTS) or set(producer_by_id) != set(EXPECTED_VARIANTS):
        raise SurfacePreviewPublishError("successor variants cannot bind producer raw variants")
    published: list[dict[str, Any]] = []
    inventory_paths: set[str] = set()
    expected_kinds = [
        "ply",
        "semantic-sidecar",
        "metrics",
        "successor-consumer-sidecar",
        "guide-skin-composite-png",
    ]
    expected_frame = {key: baseline_manifest[key] for key in frame_keys}
    for index, variant in enumerate(variants):
        where = f"successor.variants[{index}]"
        if not isinstance(variant, dict) or set(variant) != {"id", "profile_id", "source_variant_sha256", "metrics", "inventory"}:
            raise SurfacePreviewPublishError(f"{where} has unknown or missing fields")
        variant_id = variant.get("id")
        if variant.get("profile_id") != variant_id:
            raise SurfacePreviewPublishError(f"{where} has an invalid canonical id or profile")
        producer_variant = producer_by_id.get(variant_id)
        if not isinstance(producer_variant, dict):
            raise SurfacePreviewPublishError(f"{where} cannot bind its producer variant by id")
        expected_variant_sha256 = _source_variant_sha256(producer_variant, f"{where}.source_variant_sha256")
        source_variant_sha256 = variant.get("source_variant_sha256")
        if not isinstance(source_variant_sha256, str) or len(source_variant_sha256) != 64 or any(character not in "0123456789abcdef" for character in source_variant_sha256):
            raise SurfacePreviewPublishError(f"{where}.source_variant_sha256 is invalid")
        if source_variant_sha256 != expected_variant_sha256:
            raise SurfacePreviewPublishError(f"{where}.source_variant_sha256 does not match producer output")
        inventory = variant.get("inventory")
        if not isinstance(inventory, list) or len(inventory) != 5 or [item.get("kind") for item in inventory if isinstance(item, dict)] != expected_kinds:
            raise SurfacePreviewPublishError(f"{where}.inventory is not the exact five-artifact order")
        expected_paths = {
            "ply": f"{variant_id}/surface.ply",
            "semantic-sidecar": f"{variant_id}/semantic.json",
            "metrics": f"{variant_id}/metrics.json",
            "successor-consumer-sidecar": f"{variant_id}/successor.json",
            "guide-skin-composite-png": f"{variant_id}/guide-skin-composite.png",
        }
        metrics_payload: dict[str, Any] | None = None
        ply_metrics: dict[str, Any] | None = None
        surface_sha256: str | None = None
        semantic_path: Path | None = None
        sidecar_payload: dict[str, Any] | None = None
        image_entry: dict[str, Any] | None = None
        kinds: set[str] = set()
        for entry_index, entry in enumerate(inventory):
            entry_where = f"{where}.inventory[{entry_index}]"
            if not isinstance(entry, dict):
                raise SurfacePreviewPublishError(f"{entry_where} must be an object")
            kind = entry.get("kind")
            if kind not in expected_kinds or kind in kinds:
                raise SurfacePreviewPublishError(f"{entry_where}.kind is missing or duplicated")
            extra_fields = {"guide-skin-composite-png": {"width", "height", "views", "panels_per_view", "mode"}}.get(kind, set())
            if set(entry) != {"kind", "path", "sha256", "bytes"} | extra_fields:
                raise SurfacePreviewPublishError(f"{entry_where} has unknown or missing fields")
            kinds.add(kind)
            rel = _safe_relative(entry.get("path"), f"{entry_where}.path")
            rel_text = rel.as_posix()
            if rel_text != expected_paths[kind] or rel_text in inventory_paths or rel_text == SUCCESSOR_MANIFEST_NAME:
                raise SurfacePreviewPublishError(f"{entry_where}.path is not the canonical successor artifact path")
            inventory_paths.add(rel_text)
            artifact = bundle / rel
            if artifact.is_symlink() or not artifact.is_file():
                raise SurfacePreviewPublishError(f"{entry_where}.path is not a regular file")
            if type(entry.get("bytes")) is not int or entry["bytes"] < 0 or not isinstance(entry.get("sha256"), str) or len(entry["sha256"]) != 64 or any(character not in "0123456789abcdef" for character in entry["sha256"]):
                raise SurfacePreviewPublishError(f"{entry_where} has invalid bytes or sha256")
            actual_hash, actual_size = _sha256(artifact, rel_text)
            if actual_hash != entry["sha256"] or actual_size != entry["bytes"]:
                raise SurfacePreviewPublishError(f"successor inventory does not match {rel_text}")
            if kind == "ply":
                ply_metrics = _validate_successor_ply(artifact, rel_text)
                surface_sha256 = entry["sha256"]
            elif kind == "semantic-sidecar":
                semantic_path = artifact
            elif kind == "guide-skin-composite-png":
                image_entry = entry
                _validate_png(artifact, entry, rel_text)
                if entry["width"] != expected_frame["canvas"]["width"] or entry["height"] != expected_frame["canvas"]["height"] or entry["mode"] != expected_frame["canvas"]["mode"]:
                    raise SurfacePreviewPublishError(f"{entry_where} PNG metadata does not match baseline framing")
            elif kind == "metrics":
                metrics_payload = _read_json(artifact, MAX_METRICS_BYTES, f"{where}.metrics.json")
                _finite_json(metrics_payload, f"{where}.metrics.json")
                _bounded_json(metrics_payload, f"{where}.metrics.json")
            elif kind == "successor-consumer-sidecar":
                sidecar_payload = _validate_successor_sidecar(
                    artifact,
                    variant_id=variant_id,
                    profile_id=variant_id,
                    source_variant_sha256=source_variant_sha256,
                    source=source,
                    frame=expected_frame,
                    metrics=(
                        variant["metrics"]
                        if isinstance(variant.get("metrics"), dict)
                        else {}
                    ),
                    producer_payload=producer_payload,
                    baseline_guide=baseline_guides[variant_id],
                )
        if (
            kinds != set(expected_kinds)
            or ply_metrics is None
            or surface_sha256 is None
            or semantic_path is None
            or metrics_payload is None
            or sidecar_payload is None
            or image_entry is None
        ):
            raise SurfacePreviewPublishError(f"{where}.inventory is incomplete")
        semantic_payload = _validate_successor_semantic_sidecar(
            semantic_path,
            variant_id=variant_id,
            source_format=common.PROVISIONAL_FORM_FORMAT,
            source_variant_sha256=source_variant_sha256,
            surface_sha256=surface_sha256,
            ply_metrics=ply_metrics,
            descriptor_owners=profile_binding["variants"][variant_id]["descriptor_owners"],
        )
        if variant.get("metrics") != metrics_payload:
            raise SurfacePreviewPublishError(f"{where}.metrics does not match the inventoried metrics.json")
        if not isinstance(variant.get("metrics"), dict):
            raise SurfacePreviewPublishError(f"{where}.metrics must be an object")
        _validate_component_visualization_metrics(
            metrics_payload,
            allowed_owners=profile_binding["variants"][variant_id]["descriptor_owners"],
            expected_component_count=27,
            expected_recipe_counts=EXPECTED_SUCCESSOR_COMPONENT_RECIPE_COUNTS,
            where=where,
        )
        _validate_successor_ply_metrics(ply_metrics, metrics_payload, where)
        published.append({
            "id": variant_id,
            "entry": image_entry,
            "metrics": metrics_payload,
            "semantic": semantic_payload,
            "sidecar": sidecar_payload,
            "binding": {
                "source": {
                    "format": common.PROVISIONAL_FORM_FORMAT,
                    "sha256": expected_source_sha256,
                    "document": source["document"],
                    "namespace": source["namespace"],
                    "resource_profile_id": source["resource_profile_id"],
                },
                "reference_scale": source["reference_scale"],
                "variant_id": variant_id,
                "profile_id": variant["profile_id"],
                "producer_variant_sha256": source_variant_sha256,
                "descriptor_owners": profile_binding["variants"][variant_id]["descriptor_owners"],
                "capture": expected_frame,
                "torso_lineage": profile_binding["variants"][variant_id]["torso_lineage"],
                "head_neck_lineage": profile_binding["variants"][variant_id]["head_neck_lineage"],
                "arm_lineage": profile_binding["variants"][variant_id]["arm_lineage"],
                "leg_lineage": profile_binding["variants"][variant_id]["leg_lineage"],
            },
        })

    actual_paths, actual_directories = _regular_artifacts(bundle)
    actual_paths -= {SUCCESSOR_MANIFEST_NAME}
    if actual_paths != inventory_paths or actual_directories != set(EXPECTED_VARIANTS):
        raise SurfacePreviewPublishError("successor bundle contains unlisted or missing regular output")
    return published, {"source": {"format": source["format"], "sha256": source["sha256"]}, "generator": generator_metadata}


def publish_surface_preview(
    reviews_root: Path,
    input_path: Path,
    *,
    generator: Path | None = None,
    successor_generator: Path | None = None,
    creature_kernel: Path | None = None,
    review_id: str = "surface-preview",
    title: str = "Baseline-versus-successor surface comparison",
) -> dict[str, Any]:
    """Run producer and both consumers in temp space and publish four pairs."""

    try:
        stable_id = validate_id(review_id, "review id")
    except ValidationError as exc:
        raise SurfacePreviewPublishError(str(exc)) from exc
    if not isinstance(title, str) or not title.strip() or len(title) > 512:
        raise SurfacePreviewPublishError("review title must be a non-empty string no longer than 512 characters")
    try:
        input_source = _validate_input(input_path)
    except (ProvisionalFormPublishError, OSError, ValueError) as exc:
        raise SurfacePreviewPublishError(str(exc)) from exc
    reviews_root = _prepare_reviews_root(reviews_root)
    executable = (creature_kernel or default_creature_kernel()).absolute()
    generator_path = (generator or default_generator()).absolute()
    successor_generator_path = (successor_generator or default_successor_generator()).absolute()
    with tempfile.TemporaryDirectory(
        prefix=".ck-surface-preview-", dir=reviews_root.parent
    ) as temp_name:
        work = Path(temp_name)
        input_copy = work / "input.json"
        producer_output = work / "provisional-form.json"
        baseline_bundle = work / "baseline-bundle"
        successor_bundle = work / "successor-bundle"
        try:
            _copy_input_reference(input_source, input_copy)
        except (ProvisionalFormPublishError, OSError, ValueError) as exc:
            raise SurfacePreviewPublishError(str(exc)) from exc
        input_evidence = _validate_input_evidence(
            _read_input_evidence(input_copy), "source evidence"
        )
        stdout, stderr, returncode = _run_bounded(
            [str(executable), "inspect-provisional-form", "--input", str(input_copy)],
            timeout=INSPECTION_TIMEOUT_SECONDS,
            label="creature-kernel inspection",
        )
        if returncode != 0:
            detail = stderr.decode("utf-8", errors="replace").strip()[:240]
            raise SurfacePreviewPublishError(f"creature-kernel inspection failed ({returncode}){': ' + detail if detail else ''}")
        try:
            payload = _parse_inspection(stdout)
        except (ProvisionalFormPublishError, OSError, ValueError) as exc:
            raise SurfacePreviewPublishError(str(exc)) from exc
        if payload.get("format") != common.PROVISIONAL_FORM_FORMAT:
            raise SurfacePreviewPublishError("creature-kernel inspection did not produce v11")
        producer_output.write_text(
            _compact_canonical_json(payload), encoding="utf-8"
        )
        producer_sha256, _ = _sha256(producer_output, "producer envelope output")
        producer_evidence = _validate_producer_evidence(
            _read_producer_evidence(producer_output), "producer envelope evidence"
        )
        if producer_evidence["producer_envelope_sha256"] != producer_sha256:
            raise SurfacePreviewPublishError(
                "producer envelope evidence does not match the consumed producer output"
            )
        _, generator_stderr, generator_returncode = _run_bounded(
            [sys.executable, str(generator_path), "--input", str(producer_output), "--output", str(baseline_bundle)],
            timeout=GENERATOR_TIMEOUT_SECONDS,
            label="baseline surface generator",
        )
        if generator_returncode != 0:
            detail = generator_stderr.decode("utf-8", errors="replace").strip()[:240]
            raise SurfacePreviewPublishError(f"baseline surface generator failed ({generator_returncode}){': ' + detail if detail else ''}")
        published_baseline, baseline_metadata = _validate_bundle(baseline_bundle, producer_sha256, payload)
        baseline_manifest = _read_json(baseline_bundle / MANIFEST_NAME, MAX_MANIFEST_BYTES, MANIFEST_NAME)

        _, successor_stderr, successor_returncode = _run_bounded(
            [sys.executable, str(successor_generator_path), "--input", str(producer_output), "--output", str(successor_bundle)],
            timeout=GENERATOR_TIMEOUT_SECONDS,
            label="successor surface generator",
        )
        if successor_returncode != 0:
            detail = successor_stderr.decode("utf-8", errors="replace").strip()[:240]
            raise SurfacePreviewPublishError(f"successor surface generator failed ({successor_returncode}){': ' + detail if detail else ''}")
        published_successor, successor_metadata = _validate_successor_bundle(
            successor_bundle,
            producer_sha256,
            payload,
            baseline_manifest,
            baseline_metadata["regional_guides"],
        )
        baseline_by_id = {item["id"]: item for item in published_baseline}
        successor_by_id = {item["id"]: item for item in published_successor}
        if set(baseline_by_id) != set(EXPECTED_VARIANTS) or set(successor_by_id) != set(EXPECTED_VARIANTS):
            raise SurfacePreviewPublishError("published baseline and successor variants do not contain the exact canonical id set")
        for variant_id in EXPECTED_VARIANTS:
            if baseline_by_id[variant_id].get("binding") != successor_by_id[variant_id].get("binding"):
                raise SurfacePreviewPublishError(f"baseline and successor canonical binding disagree for {variant_id}")
        variant_titles = {
            "neutral-v0": "Neutral",
            "broad-soft-v0": "Broad soft",
            "lean-readable-v0": "Lean readable",
            "depth-forward-v0": "Depth forward",
        }
        manifest_path = work / "review-manifest.json"
        groups = []
        for variant_id in EXPECTED_VARIANTS:
            baseline_item = baseline_by_id[variant_id]
            successor_item = successor_by_id[variant_id]
            title_prefix = variant_titles[variant_id]
            groups.append({
                "id": variant_id,
                "title": f"{title_prefix} ({variant_id})",
                "selection_mode": "none",
                "items": [
                    {
                        "id": f"{variant_id}-baseline",
                        "title": f"{title_prefix} — baseline",
                        "source": str(baseline_bundle / baseline_item["entry"]["path"]),
                        "description": "Baseline analytic-form composite: columns front/side/three-quarter; rows control guide (not geometry), consumed fields (exact pre-union components), and final skin (smooth union).",
                        "metadata": {
                            "variant_id": variant_id,
                            "source_role": "baseline",
                            "source_format": common.PROVISIONAL_FORM_FORMAT,
                            "source_sha256": producer_sha256,
                            "generator": baseline_metadata["generator"],
                            "views": list(EXPECTED_VIEWS),
                            "panels_per_view": 3,
                            "variant_binding_sha256": hashlib.sha256(canonical_json(baseline_item["binding"]).encode("utf-8")).hexdigest(),
                        },
                    },
                    {
                        "id": f"{variant_id}-successor",
                        "title": f"{title_prefix} — successor",
                        "source": str(successor_bundle / successor_item["entry"]["path"]),
                        "description": "Successor profile-sweep composite: columns front/side/three-quarter; rows control guide (not geometry), consumed fields (exact pre-union components), and final skin (smooth union).",
                        "metadata": {
                            "variant_id": variant_id,
                            "source_role": "successor",
                            "source_format": SUCCESSOR_PREVIEW_FORMAT,
                            "source_sha256": producer_sha256,
                            "consumer_id": SUCCESSOR_CONSUMER_ID,
                            "successor_region_id": SUCCESSOR_REGION_ID,
                            "generator": successor_metadata["generator"],
                            "views": list(EXPECTED_VIEWS),
                            "panels_per_view": 3,
                            "variant_binding_sha256": hashlib.sha256(canonical_json(successor_item["binding"]).encode("utf-8")).hexdigest(),
                        },
                    },
                ],
            })
        descriptor_snapshot = _validate_input_evidence({
            **input_evidence,
            **producer_evidence,
        }, "review.subject_context.descriptor_snapshot", max_len=common.MAX_CONTEXT_JSON)
        _validate_producer_evidence(
            descriptor_snapshot, "review.subject_context.descriptor_snapshot"
        )
        if descriptor_snapshot["producer_envelope_sha256"] != producer_sha256:
            raise SurfacePreviewPublishError(
                "review lineage does not bind the consumed producer envelope"
            )
        manifest_path.write_text(canonical_json({
            "schema_version": 1,
            "id": stable_id,
            "title": title,
            "description": "Disposable baseline-versus-successor comparison using one source and one shared capture frame; publication itself is not production geometry or acceptance evidence.",
            "instructions": "For each variant, compare baseline first and successor second. Appraise overall creature coherence and recognizability, connected joints/extremities/tail, silhouette, and meaningful differentiation between variants. This gallery records no acceptance decision.",
            "subject_context": {
                "descriptor_snapshot": descriptor_snapshot,
            },
            "groups": groups,
        }), encoding="utf-8")
        try:
            summary = publish_session(reviews_root, manifest_path)
        except (ValidationError, PublishError, OSError) as exc:
            raise SurfacePreviewPublishError(f"could not publish surface preview: {exc}") from exc
    return {**summary, "kind": "surface-preview", "variants": len(EXPECTED_VARIANTS), "images": len(EXPECTED_VARIANTS) * 2}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path, help="reviews root (created if its parent exists)")
    parser.add_argument("--input", required=True, type=Path, help="body-document JSON input")
    parser.add_argument("--generator", type=Path, default=None, help="experiment generator script")
    parser.add_argument("--creature-kernel", type=Path, default=None, help="creature-kernel executable")
    parser.add_argument("--id", default="surface-preview", dest="review_id")
    parser.add_argument("--successor-generator", type=Path, default=None, help="successor experiment generator script")
    parser.add_argument("--title", default="Baseline-versus-successor surface comparison")
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        summary = publish_surface_preview(args.root, args.input, generator=args.generator, successor_generator=args.successor_generator, creature_kernel=args.creature_kernel, review_id=args.review_id, title=args.title)
    except (SurfacePreviewPublishError, ProvisionalFormPublishError, ValidationError, PublishError, OSError) as exc:
        print(f"publish-surface-preview failed: {exc}", file=sys.stderr)
        return 2
    print(canonical_json(summary), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

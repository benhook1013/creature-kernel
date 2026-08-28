#!/usr/bin/env python3
"""Publish the four rendered images from a completed structural gallery."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import stat
import struct
import sys
import tempfile
import zlib
from pathlib import Path, PurePosixPath
from typing import Any

# This file is also loaded directly by the disposable evidence probe. Python
# does not add a file-loaded module's sibling directory to sys.path, so make
# the natural imports below deliberate before loading them.
VISUAL_REVIEW_ROOT = Path(__file__).resolve().parent
if str(VISUAL_REVIEW_ROOT) not in sys.path:
    sys.path.insert(0, str(VISUAL_REVIEW_ROOT))

import common
from common import ValidationError, canonical_json, validate_id
from publish import PublishError, publish_session

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT_ROOT = REPOSITORY_ROOT / "experiments" / "current-form-surface-preview"
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))
import generate_structural_profile_sources as profile_source_generator  # noqa: E402
import structural_embodiment_gallery as gallery_generator  # noqa: E402


class StructuralEmbodimentPublishError(RuntimeError):
    """A bounded, fail-closed structural gallery publication error."""


GALLERY_FORMAT = "creature-kernel.disposable-structural-embodiment-gallery.v1"
MANIFEST_FORMAT = "creature-kernel.disposable-structural-embodiment-gallery-manifest.v1"
POSE_FORMAT = "creature-kernel.disposable-structural-embodiment-shared-pose.v1"
MANIFEST_FILE = "structural-embodiment-gallery-manifest.json"
POSE_FILE = "structural_embodiment_shared_pose.json"
GALLERY_FILE = "structural-embodiment-gallery.png"
CANDIDATE_FILE = "structural_profile_candidates.json"
SOURCES_DIR = "sources"
SOURCE_MANIFEST_FILE = "manifest.json"
SOURCE_MANIFEST_FORMAT = "creature-kernel.disposable-structural-profile-source-manifest.v1"
CANDIDATE_FORMAT = "creature-kernel.disposable-structural-profile-candidates.v1"
PROFILE_IDS = (
    "compact_broad_short_limb_large_head",
    "tall_narrow_long_legged",
    "slender_long_limb",
    "stocky_broad_chested",
)
PROFILE_LABELS = (
    "compact, broad, short-limbed, large-head",
    "tall, narrow, long-legged",
    "slender, long-limbed",
    "stocky, broad-chested",
)
PROFILE_LABEL_BY_ID = dict(zip(PROFILE_IDS, PROFILE_LABELS))
PROFILE_SHA256 = {
    "compact_broad_short_limb_large_head": "38b9ca5f16dd5b72d745a301828663ea5e12b4acf757fe1f20aede1d5a6f4f4f",
    "tall_narrow_long_legged": "425dc28ae42726d197a6cfc3a7c2b68be97ba4c2fed471b6363b330a9aa5cfc9",
    "slender_long_limb": "f6bc35e2fa9df0ff16585ec74b61e0b8a26686e359baffe0e7ad482e56037de3",
    "stocky_broad_chested": "baed9d7b55eb45053e4b90c0b2da60861e645206ba1bdd00a2e26d8cfa79c193",
}
FROZEN_CANDIDATE_TABLE_SHA256 = "68d6e808a21daad16e1d56716124fc96b021bc492adf5171ec4e155591f45336"
FROZEN_CANDIDATE_TABLE_BYTES = 26867
FROZEN_BASE_SOURCE_SHA256 = "faf02db965a2b7f6889dfb1cd58eb79befa9c536f58adca40b14ccc955eaf533"
FROZEN_BASE_SOURCE_DOCUMENT = "stylized_digitigrade_biped_authored_form"
FROZEN_BASE_SOURCE_NAMESPACE = "main"
POSE_ID = "shared-structural-pose-v1"
NEUTRAL_VARIANT_ID = "neutral-v0"
CANVAS = {"width": 1800, "height": 2500, "mode": "RGB"}
TITLE = "Latest named structural checkpoint - Shared-pose structural embodiment gallery"
DESCRIPTION = "Candidate-scoped exploratory structural embodiment evidence; not production acceptance."
INSTRUCTIONS = "Compare all four frozen profiles. Review skeleton inhabitation, shared-pose coherence, gross skin following, and proxy coverage. The side column is exact orthographic; skeleton rows are x-ray overlays and do not depth-occlude against the skin."
ARTIFACT_NAMES = (
    "neutral.ply",
    "posed.ply",
    "skeleton.json",
    "weights.json",
    "proxies-neutral.json",
    "proxies-posed.json",
    "metrics.json",
    GALLERY_FILE,
)
PROFILE_ARTIFACT_NAMES = ARTIFACT_NAMES
ROOT_ARTIFACTS = tuple(
    sorted(
        [CANDIDATE_FILE]
        + [f"{SOURCES_DIR}/{SOURCE_MANIFEST_FILE}"]
        + [f"{SOURCES_DIR}/{profile_id}.json" for profile_id in PROFILE_IDS]
        + [f"{profile_id}/{name}" for profile_id in PROFILE_IDS for name in PROFILE_ARTIFACT_NAMES]
        + [POSE_FILE]
    )
)
TRANSFORM_CONVENTION = {
    "vectors": "column",
    "bind": "bone +Y follows endpoints; deterministic up fallback +Z then +X then +Y",
    "parent_local_bind": "inverse(parent_world_bind) * child_world_bind",
    "posed_world": "parent_posed_world * parent_local_bind * local_pose_rotation",
    "skin": "posed_world * inverse(neutral_world_bind)",
    "skinning": "classic linear blend positions and weighted rotated normalized normals",
    "proxy_radius": "unchanged",
}
EXPECTED_FILES = set(ROOT_ARTIFACTS) | {MANIFEST_FILE}
EXPECTED_DIRECTORIES = set(PROFILE_IDS) | {SOURCES_DIR}
INVENTORY_ARTIFACT_COUNT = 39
TOTAL_FILE_COUNT = 40
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_TREE_ENTRIES = 2048
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_SCANLINE_BYTES = 1 + CANVAS["width"] * 3
PNG_RAW_BYTES = PNG_SCANLINE_BYTES * CANVAS["height"]
BOUNDED_READ_CHUNK = 64 * 1024


def _error(message: str) -> StructuralEmbodimentPublishError:
    return StructuralEmbodimentPublishError(message)


def _require_fields(value: Any, expected: set[str], where: str) -> None:
    if not isinstance(value, dict):
        raise _error(f"{where} must be an object")
    if set(value) != expected:
        missing = sorted(expected - set(value))
        extra = sorted(set(value) - expected)
        detail = []
        if missing:
            detail.append("missing " + ", ".join(missing))
        if extra:
            detail.append("unknown " + ", ".join(extra))
        raise _error(f"{where} has invalid fields ({'; '.join(detail)})")


def _hash(value: Any, where: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise _error(f"{where} must be a lowercase SHA-256 digest")
    return value


def _bounded_json(value: Any, where: str, depth: int = 0) -> None:
    if depth > 96:
        raise _error(f"{where} is too deeply nested")
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise _error(f"{where} contains a non-string key")
            _bounded_json(item, f"{where}.{key}", depth + 1)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _bounded_json(item, f"{where}[{index}]", depth + 1)
    elif isinstance(value, float) and not math.isfinite(value):
        raise _error(f"{where} contains a non-finite number")


def _no_temp_provenance(value: Any, where: str = "manifest") -> None:
    if isinstance(value, str):
        normalized = value.lower().replace("\\", "/")
        if normalized.startswith("/") or "/tmp/" in normalized or "/temp/" in normalized:
            raise _error(f"{where} contains temporary or absolute path provenance")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _no_temp_provenance(item, f"{where}[{index}]")
    elif isinstance(value, dict):
        for key, item in value.items():
            _no_temp_provenance(item, f"{where}.{key}")


def _safe_relative(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise _error(f"{where} is not a safe relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts) or str(path) != value:
        raise _error(f"{where} contains path traversal")
    return value


def _regular_file(path: Path, where: str) -> os.stat_result:
    try:
        common._reject_symlink_components(path, where)
        info = path.lstat()
    except (OSError, ValidationError) as exc:
        raise _error(f"{where} is unavailable or uses a symlink") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise _error(f"{where} must be a regular non-symlink file")
    return info


def _read_bounded_file(path: Path, where: str, max_bytes: int) -> bytes:
    """Read a checked regular file through descriptor-relative no-follow opens."""
    expected = _regular_file(path, where)
    absolute = Path(os.path.abspath(os.fspath(path)))
    parent_fd: int | None = None
    file_fd: int | None = None
    try:
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
        parent_fd = os.open(absolute.anchor, directory_flags)
        for component in absolute.parts[1:-1]:
            next_fd = os.open(component, directory_flags, dir_fd=parent_fd)
            os.close(parent_fd)
            parent_fd = next_fd
        leaf_flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
        file_fd = os.open(absolute.name, leaf_flags, dir_fd=parent_fd)
        opened = os.fstat(file_fd)
        if not stat.S_ISREG(opened.st_mode):
            raise _error(f"{where} must be a regular non-symlink file")
        if (opened.st_dev, opened.st_ino) != (expected.st_dev, expected.st_ino):
            raise _error(f"{where} changed during validation")

        data = bytearray()
        read_limit = max_bytes + 1
        while len(data) < read_limit:
            chunk = os.read(file_fd, min(BOUNDED_READ_CHUNK, read_limit - len(data)))
            if not chunk:
                break
            data.extend(chunk)
        if len(data) > max_bytes:
            raise _error(f"{where} is too large")
        return bytes(data)
    except StructuralEmbodimentPublishError:
        raise
    except OSError as exc:
        raise _error(f"{where} cannot be read") from exc
    finally:
        if file_fd is not None:
            try:
                os.close(file_fd)
            except OSError:
                pass
        if parent_fd is not None:
            try:
                os.close(parent_fd)
            except OSError:
                pass


def _read_json(path: Path, where: str) -> tuple[dict[str, Any], bytes]:
    try:
        data = _read_bounded_file(path, where, common.MAX_JSON_BYTES)
        value = _decode_json_bytes(data, where)
    except StructuralEmbodimentPublishError:
        raise
    except OSError as exc:
        raise _error(f"{where} cannot be read") from exc
    return value, data


def _decode_json_bytes(data: bytes, where: str) -> dict[str, Any]:
    if len(data) > common.MAX_JSON_BYTES:
        raise _error(f"{where} is too large")

    def unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate key {key}")
            result[key] = value
        return result

    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=unique_pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError("non-finite number")),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise _error(f"{where} is not valid finite UTF-8 JSON") from exc
    _bounded_json(value, where)
    if not isinstance(value, dict):
        raise _error(f"{where} must contain an object")
    return value


def _semantic_equal(actual: Any, expected: Any, *, tolerance: float = 1.0e-12) -> bool:
    if isinstance(actual, bool) or isinstance(expected, bool):
        return type(actual) is type(expected) and actual == expected
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        return math.isclose(float(actual), float(expected), rel_tol=tolerance, abs_tol=tolerance)
    if type(actual) is not type(expected):
        return False
    if isinstance(actual, dict):
        return set(actual) == set(expected) and all(_semantic_equal(actual[key], expected[key], tolerance=tolerance) for key in actual)
    if isinstance(actual, list):
        return len(actual) == len(expected) and all(_semantic_equal(left, right, tolerance=tolerance) for left, right in zip(actual, expected))
    return actual == expected


def _scan_tree(root: Path) -> tuple[set[str], set[str]]:
    files: set[str] = set()
    directories: set[str] = set()
    count = 0

    def walk(directory: Path, relative: str) -> None:
        nonlocal count
        try:
            entries = sorted(os.scandir(directory), key=lambda entry: entry.name)
        except OSError as exc:
            raise _error("could not scan gallery tree") from exc
        for entry in entries:
            count += 1
            if count > MAX_TREE_ENTRIES:
                raise _error("gallery tree has too many entries")
            if not entry.name or "/" in entry.name or "\\" in entry.name or entry.name in {".", ".."}:
                raise _error("gallery tree contains an unsafe entry name")
            child = f"{relative}/{entry.name}" if relative else entry.name
            try:
                info = entry.stat(follow_symlinks=False)
            except OSError as exc:
                raise _error("could not stat gallery tree member") from exc
            if stat.S_ISLNK(info.st_mode):
                raise _error(f"gallery tree contains a symlink: {child}")
            if stat.S_ISDIR(info.st_mode):
                directories.add(child)
                walk(Path(entry.path), child)
            elif stat.S_ISREG(info.st_mode):
                files.add(child)
            else:
                raise _error(f"gallery tree contains a special file: {child}")

    _regular_file(root, "gallery root") if root.exists() and not root.is_dir() else None
    try:
        common._reject_symlink_components(root, "gallery root")
        info = root.lstat()
    except (OSError, ValidationError) as exc:
        raise _error("gallery root is unavailable or uses a symlink") from exc
    if not stat.S_ISDIR(info.st_mode):
        raise _error("gallery root must be a regular non-symlink directory")
    walk(root, "")
    return files, directories


def _artifact_entry(value: Any, where: str) -> dict[str, Any]:
    _require_fields(value, {"path", "sha256", "bytes"}, where)
    path = _safe_relative(value["path"], f"{where}.path")
    digest = _hash(value["sha256"], f"{where}.sha256")
    size = value["bytes"]
    if isinstance(size, bool) or not isinstance(size, int) or size < 0 or size > MAX_FILE_BYTES:
        raise _error(f"{where}.bytes is invalid")
    return {"path": path, "sha256": digest, "bytes": size}


def _expected_source_documents(candidate: dict[str, Any], candidate_data: bytes) -> dict[str, bytes]:
    if hashlib.sha256(candidate_data).hexdigest() != FROZEN_CANDIDATE_TABLE_SHA256:
        raise _error("copied candidate table bytes are not frozen")
    base_source = candidate.get("base_source")
    _require_fields(base_source, {"document", "namespace", "path", "sha256"}, "copied candidate table.base_source")
    relative = _safe_relative(base_source["path"], "copied candidate table.base_source.path")
    source_path = REPOSITORY_ROOT / relative
    source_value, source_data = _read_json(source_path, "frozen base source")
    if hashlib.sha256(source_data).hexdigest() != FROZEN_BASE_SOURCE_SHA256 or base_source != {
        "document": FROZEN_BASE_SOURCE_DOCUMENT,
        "namespace": FROZEN_BASE_SOURCE_NAMESPACE,
        "path": relative,
        "sha256": FROZEN_BASE_SOURCE_SHA256,
    }:
        raise _error("copied candidate table does not bind the frozen base source")
    try:
        outputs = profile_source_generator.generate_sources(candidate, source_value)
        expected = {
            profile_id: profile_source_generator.canonical_source_bytes(output)
            for profile_id, output in zip(PROFILE_IDS, outputs)
        }
    except profile_source_generator.ProfileGenerationError as exc:
        raise _error("could not reproduce generated sources from the copied candidate table") from exc
    if set(expected) != set(PROFILE_IDS):
        raise _error("copied candidate table did not reproduce the exact four-profile source set")
    return expected


def _validate_source_documents(
    gallery: Path,
    candidate_table: dict[str, Any],
    source_manifest: dict[str, Any],
    inventory_by_path: dict[str, dict[str, Any]],
) -> None:
    candidate_value, candidate_data = _read_json(gallery / CANDIDATE_FILE, "copied candidate table")
    expected_source_data = _expected_source_documents(candidate_value, candidate_data)
    source_manifest_path = gallery / source_manifest["path"]
    source_manifest_value, source_manifest_data = _read_json(source_manifest_path, "generated source manifest")
    source_manifest_entry = inventory_by_path[source_manifest["path"]]
    if (
        hashlib.sha256(source_manifest_data).hexdigest() != source_manifest_entry["sha256"]
        or len(source_manifest_data) != source_manifest_entry["bytes"]
    ):
        raise _error("generated source manifest changed during semantic validation")
    _require_fields(
        source_manifest_value,
        {"candidate_format", "format", "profiles", "source"},
        "generated source manifest",
    )
    if source_manifest_value["format"] != SOURCE_MANIFEST_FORMAT or source_manifest_value["candidate_format"] != CANDIDATE_FORMAT:
        raise _error("generated source manifest format is unsupported")
    source = source_manifest_value["source"]
    _require_fields(
        source,
        {"base_document", "base_namespace", "candidate_sha256", "source_sha256"},
        "generated source manifest.source",
    )
    _hash(source["candidate_sha256"], "generated source manifest.source.candidate_sha256")
    _hash(source["source_sha256"], "generated source manifest.source.source_sha256")
    if source != {
        "base_document": FROZEN_BASE_SOURCE_DOCUMENT,
        "base_namespace": FROZEN_BASE_SOURCE_NAMESPACE,
        "candidate_sha256": candidate_table["sha256"],
        "source_sha256": FROZEN_BASE_SOURCE_SHA256,
    }:
        raise _error("generated source manifest does not bind the frozen candidate and base source")

    profiles = source_manifest_value["profiles"]
    if not isinstance(profiles, list) or len(profiles) != len(PROFILE_IDS):
        raise _error("generated source manifest must contain exactly four profiles")
    if [item.get("id") if isinstance(item, dict) else None for item in profiles] != list(PROFILE_IDS):
        raise _error("generated source manifest profile order is not the frozen order")
    for index, raw in enumerate(profiles):
        profile_id = PROFILE_IDS[index]
        where = f"generated source manifest.profiles[{index}]"
        _require_fields(raw, {"bytes", "document", "file", "id", "sha256", "tail_signature"}, where)
        expected_document = f"{FROZEN_BASE_SOURCE_DOCUMENT}__structural_profile__{profile_id}"
        if raw["id"] != profile_id or raw["file"] != f"{profile_id}.json" or raw["document"] != expected_document:
            raise _error(f"{where} identity is not frozen")
        if (
            not isinstance(raw["tail_signature"], list)
            or len(raw["tail_signature"]) != 5
            or any(type(value) is not int for value in raw["tail_signature"])
        ):
            raise _error(f"{where}.tail_signature must contain exactly five integers")
        source_file = _safe_relative(raw["file"], f"{where}.file")
        source_relative = f"{SOURCES_DIR}/{source_file}"
        source_hash = _hash(raw["sha256"], f"{where}.sha256")
        source_bytes = raw["bytes"]
        if isinstance(source_bytes, bool) or not isinstance(source_bytes, int) or source_bytes <= 0 or source_bytes > MAX_FILE_BYTES:
            raise _error(f"{where}.bytes is invalid")
        if inventory_by_path[source_relative] != {
            "path": source_relative,
            "sha256": source_hash,
            "bytes": source_bytes,
        }:
            raise _error(f"{where} does not match its copied inventory entry")
        source_value, source_data = _read_json(gallery / source_relative, f"generated source {profile_id}")
        if hashlib.sha256(source_data).hexdigest() != source_hash or len(source_data) != source_bytes:
            raise _error(f"generated source {profile_id} does not match its manifest record")
        if source_data != expected_source_data[profile_id]:
            raise _error(f"generated source {profile_id} is not the exact output of the frozen candidate table")
        if not isinstance(source_value.get("source"), dict):
            raise _error(f"generated source {profile_id}.source must be an object")
        source_identity = source_value["source"]
        if source_identity.get("document") != expected_document or source_identity.get("namespace") != FROZEN_BASE_SOURCE_NAMESPACE:
            raise _error(f"generated source {profile_id} source identity is not bound to its manifest record")


def _source_semantic_inputs(source_data: bytes, profile_id: str) -> dict[str, Any]:
    source_root = _decode_json_bytes(source_data, f"generated source {profile_id}")
    body = gallery_generator._obj(source_root.get("body"), f"generated source {profile_id}.body")
    parts = gallery_generator._records_by_address(body.get("parts"), f"generated source {profile_id}.body.parts")
    joints = gallery_generator._records_by_address(body.get("joints"), f"generated source {profile_id}.body.joints")
    if len(parts) != 18 or len(joints) != 17:
        raise _error(f"generated source {profile_id} does not contain the exact semantic structure")
    for index, joint in enumerate(joints.values()):
        gallery_generator._identity_frame(joint.get("proximal_frame"), f"generated source {profile_id}.joint[{index}].proximal_frame")
        gallery_generator._identity_frame(joint.get("distal_frame"), f"generated source {profile_id}.joint[{index}].distal_frame")
    try:
        world_points, root_part = gallery_generator._structure_world_points(parts)
    except gallery_generator.GalleryError as exc:
        raise _error(f"generated source {profile_id} has invalid Part containment") from exc
    distal_parts: set[tuple[str, tuple[str, ...], str, str]] = set()
    for joint in joints.values():
        distal = gallery_generator._address_key(joint["distal"], "source Joint distal")
        proximal = gallery_generator._address_key(joint["proximal"], "source Joint proximal")
        if distal not in parts or proximal not in parts or distal in distal_parts:
            raise _error(f"generated source {profile_id} Joint coverage is incomplete")
        distal_parts.add(distal)
    if distal_parts != set(parts) - {root_part}:
        raise _error(f"generated source {profile_id} Joint coverage is incomplete")
    return {"root": source_root, "parts": parts, "joints": joints, "world_points": world_points, "root_part": root_part}


def _published_candidate(
    profile_id: str,
    skeleton: dict[str, Any],
    weights: dict[str, Any],
    neutral_proxies: dict[str, Any],
    source: dict[str, Any],
) -> dict[str, Any]:
    hierarchy = skeleton["neutral"]["bones"]
    if not isinstance(hierarchy, list) or len(hierarchy) != 18:
        raise _error(f"{profile_id} neutral skeleton must contain exactly 18 bones")
    bones: list[dict[str, Any]] = []
    mapping: list[dict[str, Any]] = []
    seen_bones: set[str] = set()
    seen_joints: set[tuple[str, tuple[str, ...], str, str]] = set()
    for index, raw in enumerate(hierarchy):
        if not isinstance(raw, dict):
            raise _error(f"{profile_id} neutral skeleton bone[{index}] must be an object")
        bone = dict(raw)
        bone_id = bone.get("id")
        if not isinstance(bone_id, str) or bone_id in seen_bones:
            raise _error(f"{profile_id} neutral skeleton contains duplicate or invalid bone IDs")
        seen_bones.add(bone_id)
        if bone_id == "bone-source-part-root":
            if bone.get("kind") != "synthetic-source-part-root" or bone.get("parent") is not None:
                raise _error(f"{profile_id} neutral skeleton root identity is invalid")
            root_part = source["root_part"]
            source_part = bone.get("source_part")
            if gallery_generator._address_key(source_part, f"{profile_id} root source_part") != root_part:
                raise _error(f"{profile_id} neutral skeleton root is not source-bound")
            expected_root = source["world_points"][root_part]
            root_endpoint = gallery_generator._vector(bone["b"], f"{profile_id} neutral skeleton root endpoint")
            if max(abs(actual - expected) for actual, expected in zip(root_endpoint, expected_root)) <= 1.0e-12:
                bone["b"] = list(expected_root)
            bone.update({"owned_part": source_part, "source_parts": [source_part], "surface_anchor_rule": "centroid of the complete neutral surface, with lexicographically stable farthest-vertex fallback"})
        else:
            if bone.get("kind") != "derived-joint" or not isinstance(bone.get("joint"), dict):
                raise _error(f"{profile_id} neutral skeleton derived bone identity is invalid")
            joint_key = gallery_generator._address_key(bone["joint"], f"{profile_id} bone joint")
            if joint_key in seen_joints or joint_key not in source["joints"]:
                raise _error(f"{profile_id} neutral skeleton does not cover the exact source Joint set")
            joint = source["joints"][joint_key]
            proximal = joint["proximal"]
            distal = joint["distal"]
            bone.update({"joint": joint["address"], "proximal": proximal, "distal": distal, "owned_part": distal, "source_parts": [proximal, distal]})
            mapping.append({"bone_id": bone_id, "joint": joint["address"]})
            seen_joints.add(joint_key)
        bones.append(bone)
    if seen_joints != set(source["joints"]):
        raise _error(f"{profile_id} neutral skeleton does not cover every source Joint")
    return {
        "hierarchy": {"bones": bones, "joint_address_to_bone": mapping},
        "weights": {"vertex_count": weights["vertex_count"], "influences": weights["influences"]},
        "proxies": neutral_proxies["proxies"],
    }


def _parse_ply_bytes(data: bytes, where: str) -> dict[str, Any]:
    try:
        with tempfile.TemporaryDirectory(prefix="ck-structural-publication-ply-") as temporary:
            path = Path(temporary) / "artifact.ply"
            path.write_bytes(data)
            return gallery_generator.bridge._parse_ply(path, expected_sha256=hashlib.sha256(data).hexdigest())
    except gallery_generator.bridge.BridgeError as exc:
        raise _error(f"{where} is not a valid watertight PLY: {exc}") from exc
    except OSError as exc:
        raise _error(f"{where} could not be staged for semantic validation") from exc


def _validate_profile_semantics(
    profile_id: str,
    profile_manifest: dict[str, Any],
    artifact_data: dict[str, bytes],
    source: dict[str, Any],
    pose: dict[str, Any],
) -> dict[str, Any]:
    prefix = f"{profile_id}/"

    def data(name: str) -> bytes:
        try:
            return artifact_data[prefix + name]
        except KeyError as exc:
            raise _error(f"{profile_id} semantic artifact is missing: {name}") from exc

    neutral_data = data("neutral.ply")
    posed_data = data("posed.ply")
    neutral = _parse_ply_bytes(neutral_data, f"{profile_id} neutral.ply")
    posed = _parse_ply_bytes(posed_data, f"{profile_id} posed.ply")
    skeleton = _decode_json_bytes(data("skeleton.json"), f"{profile_id} skeleton.json")
    weights = _decode_json_bytes(data("weights.json"), f"{profile_id} weights.json")
    neutral_proxies = _decode_json_bytes(data("proxies-neutral.json"), f"{profile_id} proxies-neutral.json")
    posed_proxies = _decode_json_bytes(data("proxies-posed.json"), f"{profile_id} proxies-posed.json")
    metrics = _decode_json_bytes(data("metrics.json"), f"{profile_id} metrics.json")

    _require_fields(skeleton, {"convention", "format", "neutral", "posed", "profile_id"}, f"{profile_id} skeleton.json")
    if skeleton["profile_id"] != profile_id or skeleton["format"] != GALLERY_FORMAT or skeleton["convention"] != {
        "matrices": "row-major storage with column-vector multiplication",
        "vectors": "column",
    }:
        raise _error(f"{profile_id} skeleton convention is invalid")
    _require_fields(skeleton["neutral"], {"bind_parent_local", "bind_world", "bones"}, f"{profile_id} skeleton.neutral")
    _require_fields(skeleton["posed"], {"bones", "posed_world", "skin"}, f"{profile_id} skeleton.posed")
    for state, matrices in (("neutral", ("bind_world", "bind_parent_local")), ("posed", ("posed_world", "skin"))):
        if any(not isinstance(skeleton[state][key], dict) for key in matrices):
            raise _error(f"{profile_id} skeleton.{state} matrices are invalid")
    neutral_bones = skeleton["neutral"]["bones"]
    posed_bones = skeleton["posed"]["bones"]
    if not isinstance(neutral_bones, list) or not isinstance(posed_bones, list) or len(neutral_bones) != 18 or len(posed_bones) != 18:
        raise _error(f"{profile_id} skeleton states must contain exactly 18 bones")
    for state_name, bones in (("neutral", neutral_bones), ("posed", posed_bones)):
        for index, bone in enumerate(bones):
            if not isinstance(bone, dict):
                raise _error(f"{profile_id} skeleton.{state_name}.bones[{index}] must be an object")
            required = {"a", "b", "id", "kind", "length", "parent"}
            if bone.get("kind") == "synthetic-source-part-root":
                required.add("source_part")
            if bone.get("kind") == "derived-joint":
                required.add("joint")
            _require_fields(bone, required, f"{profile_id} skeleton.{state_name}.bones[{index}]")
            gallery_generator._vector(bone["a"], f"{profile_id} skeleton.{state_name}.bones[{index}].a")
            gallery_generator._vector(bone["b"], f"{profile_id} skeleton.{state_name}.bones[{index}].b")
            if isinstance(bone["length"], bool) or not isinstance(bone["length"], (int, float)) or not math.isfinite(float(bone["length"])):
                raise _error(f"{profile_id} skeleton.{state_name}.bones[{index}].length is invalid")
    if [bone["id"] for bone in neutral_bones] != [bone["id"] for bone in posed_bones]:
        raise _error(f"{profile_id} neutral and posed skeleton bone order differs")
    for neutral_bone, posed_bone in zip(neutral_bones, posed_bones):
        for key in ("id", "kind", "length", "parent", "source_part", "joint", "proximal", "distal"):
            if neutral_bone.get(key) != posed_bone.get(key):
                raise _error(f"{profile_id} neutral and posed skeleton lineage differs")

    _require_fields(weights, {"dominant", "format", "influences", "profile_id", "vertex_count"}, f"{profile_id} weights.json")
    if weights["format"] != GALLERY_FORMAT or weights["profile_id"] != profile_id:
        raise _error(f"{profile_id} weights lineage is invalid")
    _require_fields(neutral_proxies, {"format", "profile_id", "proxies", "radius_transform", "state"}, f"{profile_id} proxies-neutral.json")
    _require_fields(posed_proxies, {"format", "profile_id", "proxies", "radius_transform", "state"}, f"{profile_id} proxies-posed.json")
    if neutral_proxies["format"] != GALLERY_FORMAT or neutral_proxies["profile_id"] != profile_id or neutral_proxies["state"] != "neutral" or neutral_proxies["radius_transform"] != "unchanged":
        raise _error(f"{profile_id} neutral proxy lineage is invalid")
    if posed_proxies["format"] != GALLERY_FORMAT or posed_proxies["profile_id"] != profile_id or posed_proxies["state"] != "posed" or posed_proxies["radius_transform"] != "unchanged":
        raise _error(f"{profile_id} posed proxy lineage is invalid")
    if not isinstance(neutral_proxies["proxies"], list) or not isinstance(posed_proxies["proxies"], list):
        raise _error(f"{profile_id} proxy lists are invalid")

    candidate = _published_candidate(profile_id, skeleton, weights, neutral_proxies, source)
    try:
        gallery_generator._validate_candidate_geometry(profile_id, candidate, neutral, source["parts"], source["joints"])
        prepared = gallery_generator._prepare_profile({"id": profile_id, "candidate": candidate, "neutral": neutral}, pose)
    except gallery_generator.GalleryError as exc:
        raise _error(f"{profile_id} semantic structure is invalid: {exc}") from exc

    expected_skeleton = {
        "convention": skeleton["convention"],
        "format": GALLERY_FORMAT,
        "profile_id": profile_id,
        "neutral": {
            "bones": prepared["neutral_skeleton"],
            "bind_world": {key: gallery_generator._round_matrix(value) for key, value in sorted(prepared["world_bind"].items())},
            "bind_parent_local": {key: gallery_generator._round_matrix(value) for key, value in sorted(prepared["local_bind"].items())},
        },
        "posed": {
            "bones": prepared["posed_skeleton"],
            "posed_world": {key: gallery_generator._round_matrix(value) for key, value in sorted(prepared["posed_world"].items())},
            "skin": {key: gallery_generator._round_matrix(value) for key, value in sorted(prepared["skin"].items())},
        },
    }
    if not _semantic_equal(skeleton, expected_skeleton):
        raise _error(f"{profile_id} skeleton does not match deterministic source bind and pose transforms")

    expected_dominant = [{"bone_id": bone_id, "max_weight": weight} for bone_id, weight in prepared["dominant"]]
    expected_weights = {
        "format": GALLERY_FORMAT,
        "profile_id": profile_id,
        "vertex_count": len(neutral["vertices"]),
        "influences": candidate["weights"]["influences"],
        "dominant": expected_dominant,
    }
    if weights != expected_weights:
        raise _error(f"{profile_id} weights or dominant evidence is inconsistent with the complete normalized influence rows")

    expected_neutral_proxies = {"format": GALLERY_FORMAT, "profile_id": profile_id, "state": "neutral", "radius_transform": "unchanged", "proxies": prepared["neutral_proxies"]}
    expected_posed_proxies = {"format": GALLERY_FORMAT, "profile_id": profile_id, "state": "posed", "radius_transform": "unchanged", "proxies": prepared["posed_proxies"]}
    if not _semantic_equal(neutral_proxies, expected_neutral_proxies) or not _semantic_equal(posed_proxies, expected_posed_proxies):
        raise _error(f"{profile_id} proxy endpoints, partitions, radii, or posed transforms are inconsistent")

    expected_posed_data = gallery_generator._ply_bytes(prepared["posed_vertices"], prepared["posed_normals"], neutral["faces"])
    if posed_data != expected_posed_data:
        raise _error(f"{profile_id} posed PLY is not the deterministic weighted skinning result")

    expected_metrics = {
        "format": GALLERY_FORMAT,
        "profile_id": profile_id,
        "neutral_vertex_count": len(neutral["vertices"]),
        "posed_vertex_count": len(posed["vertices"]),
        "face_count": len(neutral["faces"]),
        "bone_count": len(prepared["neutral_skeleton"]),
        "proxy_count": len(prepared["neutral_proxies"]),
        "neutral_bounds": {"min": list(gallery_generator._bounds(neutral["vertices"])[0]), "max": list(gallery_generator._bounds(neutral["vertices"])[1])},
        "posed_bounds": {"min": list(gallery_generator._bounds(prepared["posed_vertices"])[0]), "max": list(gallery_generator._bounds(prepared["posed_vertices"])[1])},
        "pose_rule_count": len(prepared["pose_rules"]),
        "source_joint_frame_policy": "identity-only-validated-from-hash-bound-structure",
        "gallery_global_world_bound": profile_manifest["gallery"]["global_world_bound"],
    }
    if not _semantic_equal(metrics, expected_metrics) or not _semantic_equal(profile_manifest["metrics"], metrics):
        raise _error(f"{profile_id} metrics are inconsistent with the validated semantic artifacts")
    return prepared


def _validate_pose_bytes(pose_data: bytes) -> dict[str, Any]:
    checked_in = EXPERIMENT_ROOT / POSE_FILE
    checked_in_data = _read_bounded_file(checked_in, "checked-in shared pose", common.MAX_JSON_BYTES)
    if pose_data != checked_in_data:
        raise _error("gallery shared pose is not the exact checked-in shared pose recipe")
    with tempfile.TemporaryDirectory(prefix="ck-checked-in-shared-pose-") as temporary:
        safe_copy = Path(temporary) / POSE_FILE
        safe_copy.write_bytes(checked_in_data)
        try:
            pose, reread = gallery_generator._load_pose_with_bytes(safe_copy)
        except gallery_generator.GalleryError as exc:
            raise _error(f"checked-in shared pose is invalid: {exc}") from exc
        if reread != checked_in_data:
            raise _error("checked-in shared pose changed during validation")
    return pose


def _validate_png(data: bytes, where: str) -> None:
    if not data.startswith(PNG_SIGNATURE):
        raise _error(f"{where} is not a PNG")
    offset = len(PNG_SIGNATURE)
    seen_ihdr = False
    seen_idat = False
    seen_iend = False
    idat = bytearray()
    width = height = None
    while offset < len(data):
        if len(data) - offset < 12:
            raise _error(f"{where} has a truncated PNG chunk")
        length = struct.unpack_from(">I", data, offset)[0]
        offset += 4
        chunk_type = data[offset:offset + 4]
        offset += 4
        if len(chunk_type) != 4 or offset + length + 4 > len(data):
            raise _error(f"{where} has an invalid PNG chunk length")
        payload = data[offset:offset + length]
        offset += length
        expected_crc = struct.unpack_from(">I", data, offset)[0]
        offset += 4
        if zlib.crc32(chunk_type + payload) & 0xFFFFFFFF != expected_crc:
            raise _error(f"{where} has an invalid PNG CRC")
        if chunk_type == b"IHDR":
            if seen_ihdr or length != 13 or offset - length - 12 != len(PNG_SIGNATURE):
                raise _error(f"{where} has an invalid PNG header")
            width, height, bit_depth, color_type, compression, filtering, interlace = struct.unpack(
                ">IIBBBBB", payload
            )
            if (width, height, bit_depth, color_type, compression, filtering, interlace) != (1800, 2500, 8, 2, 0, 0, 0):
                raise _error(f"{where} is not a non-interlaced 8-bit RGB 1800x2500 PNG")
            seen_ihdr = True
        elif chunk_type == b"IDAT":
            if not seen_ihdr or seen_iend:
                raise _error(f"{where} has an invalid IDAT position")
            seen_idat = True
            idat.extend(payload)
        elif chunk_type == b"IEND":
            if not seen_ihdr or not seen_idat or seen_iend or length != 0:
                raise _error(f"{where} has an invalid IEND")
            seen_iend = True
            if offset != len(data):
                raise _error(f"{where} has trailing data")
        elif seen_iend:
            raise _error(f"{where} has data after IEND")
        elif chunk_type[0] & 0x20 == 0:
            raise _error(f"{where} contains an unknown critical chunk: {chunk_type.decode('ascii', 'replace')}")
    if not (seen_ihdr and seen_idat and seen_iend and width == 1800 and height == 2500):
        raise _error(f"{where} is incomplete")
    expected = PNG_RAW_BYTES
    try:
        decompressor = zlib.decompressobj()
        raw = decompressor.decompress(bytes(idat), expected + 1)
    except zlib.error as exc:
        raise _error(f"{where} contains invalid image data") from exc
    if (
        len(raw) > expected
        or decompressor.unconsumed_tail
        or decompressor.unused_data
        or not decompressor.eof
    ):
        raise _error(f"{where} contains invalid or trailing image data")
    if len(raw) != expected:
        raise _error(f"{where} has invalid RGB scanline data")
    if any(raw[offset] > 4 for offset in range(0, expected, PNG_SCANLINE_BYTES)):
        raise _error(f"{where} contains an invalid scanline filter byte")


def validate_structural_embodiment_gallery(gallery: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]], str, int]:
    """Validate disposable structural-gallery evidence for developer tooling.

    The returned manifest, profile, hash, and byte evidence is an internal
    publication input. This validates neither a runtime package nor a durable
    format or adapter input, and makes no claim about contact, deformation,
    physical response, or R3.
    """
    files, directories = _scan_tree(gallery)
    if (
        len(ROOT_ARTIFACTS) != INVENTORY_ARTIFACT_COUNT
        or len(EXPECTED_FILES) != TOTAL_FILE_COUNT
        or len(files) != TOTAL_FILE_COUNT
        or files != EXPECTED_FILES
        or directories != EXPECTED_DIRECTORIES
    ):
        raise _error("gallery tree does not contain exactly 39 inventoried files and 40 total files")
    manifest, manifest_bytes = _read_json(gallery / MANIFEST_FILE, "gallery manifest")
    _require_fields(
        manifest,
        {"format", "status", "gallery_format", "pose_format", "pose_sha256", "pose_id", "candidate_table", "source_manifest", "profile_ids", "profiles", "global_world_bound", "canvas", "transform_convention", "boundary", "lineage", "artifacts"},
        "gallery manifest",
    )
    if manifest["format"] != MANIFEST_FORMAT or manifest["status"] != "success" or manifest["gallery_format"] != GALLERY_FORMAT or manifest["pose_format"] != POSE_FORMAT:
        raise _error("gallery manifest is not the expected successful structural gallery schema")
    if manifest["pose_id"] != POSE_ID:
        raise _error("gallery pose ID is not the frozen shared scenario")
    _hash(manifest["pose_sha256"], "gallery manifest.pose_sha256")
    if manifest["profile_ids"] != list(PROFILE_IDS):
        raise _error("gallery profile order is not the exact frozen order")
    _require_fields(manifest["candidate_table"], {"kind", "path", "sha256", "bytes", "profile_sha256"}, "gallery manifest.candidate_table")
    candidate_table = manifest["candidate_table"]
    if candidate_table["kind"] != "candidate-table" or candidate_table["path"] != CANDIDATE_FILE or candidate_table["sha256"] != FROZEN_CANDIDATE_TABLE_SHA256 or candidate_table["bytes"] != FROZEN_CANDIDATE_TABLE_BYTES:
        raise _error("gallery candidate table is not the exact frozen table")
    if not isinstance(candidate_table["profile_sha256"], dict) or candidate_table["profile_sha256"] != PROFILE_SHA256:
        raise _error("gallery candidate-table profile identities are not frozen")
    _require_fields(
        manifest["source_manifest"],
        {"kind", "path", "sha256", "bytes", "base_source_sha256"},
        "gallery manifest.source_manifest",
    )
    source_manifest = manifest["source_manifest"]
    _hash(source_manifest["sha256"], "gallery manifest.source_manifest.sha256")
    if (
        source_manifest["kind"] != "generated-source-manifest"
        or source_manifest["path"] != f"{SOURCES_DIR}/{SOURCE_MANIFEST_FILE}"
        or source_manifest["base_source_sha256"] != FROZEN_BASE_SOURCE_SHA256
    ):
        raise _error("gallery source manifest metadata is not source-bound")
    if isinstance(source_manifest["bytes"], bool) or not isinstance(source_manifest["bytes"], int) or source_manifest["bytes"] < 0 or source_manifest["bytes"] > MAX_FILE_BYTES:
        raise _error("gallery source manifest byte count is invalid")
    _require_fields(manifest["canvas"], {"width", "height", "mode", "columns", "rows"}, "gallery manifest.canvas")
    if manifest["canvas"] != {**CANVAS, "columns": ["front", "side", "three-quarter"], "rows": ["neutral skin+skeleton", "posed skin+skeleton", "per-vertex dominant-bone hue/max-weight brightness", "neutral skin+proxies", "posed skin+proxies"]}:
        raise _error("gallery canvas schema is not exact")
    _require_fields(manifest["lineage"], {"source", "build", "scenario"}, "gallery manifest.lineage")
    if manifest["lineage"] != {"source": "frozen candidate table, generated source manifest/documents, hash-bound bridge manifests, bridge JSON, neutral PLYs, and per-profile identity-frame structures", "build": "shared deterministic structural embodiment gallery v1", "scenario": {"id": POSE_ID, "surface_variant_id": NEUTRAL_VARIANT_ID, "pose_id": POSE_ID}}:
        raise _error("gallery lineage is not exact")
    if manifest["boundary"] != "candidate-scoped disposable structural evidence; no muscles, anatomy, IK, contacts, runtime, engine, or VR":
        raise _error("gallery boundary is not exact")
    if manifest["transform_convention"] != TRANSFORM_CONVENTION:
        raise _error("gallery transform convention is not exact")
    _no_temp_provenance(manifest)

    inventory = manifest["artifacts"]
    if not isinstance(inventory, list) or len(inventory) != INVENTORY_ARTIFACT_COUNT:
        raise _error("gallery manifest must inventory exactly 39 artifacts")
    normalized_inventory = [_artifact_entry(item, f"gallery manifest.artifacts[{index}]") for index, item in enumerate(inventory)]
    if [item["path"] for item in normalized_inventory] != list(ROOT_ARTIFACTS):
        raise _error("gallery artifact inventory order or paths are not exact")
    inventory_by_path = {item["path"]: item for item in normalized_inventory}
    if inventory_by_path[CANDIDATE_FILE] != {
        "path": CANDIDATE_FILE,
        "sha256": candidate_table["sha256"],
        "bytes": candidate_table["bytes"],
    }:
        raise _error("gallery candidate table does not match its copied inventory entry")
    if inventory_by_path[source_manifest["path"]] != {
        "path": source_manifest["path"],
        "sha256": source_manifest["sha256"],
        "bytes": source_manifest["bytes"],
    }:
        raise _error("gallery source manifest does not match its copied inventory entry")
    _validate_source_documents(gallery, candidate_table, source_manifest, inventory_by_path)
    if manifest["pose_sha256"] != inventory_by_path[POSE_FILE]["sha256"]:
        raise _error("gallery pose hash does not match its inventoried artifact")
    artifact_data: dict[str, bytes] = {}
    for relative, entry in inventory_by_path.items():
        try:
            data = _read_bounded_file(gallery / relative, f"gallery artifact {relative}", MAX_FILE_BYTES)
            size = len(data)
            digest = hashlib.sha256(data).hexdigest()
        except StructuralEmbodimentPublishError:
            raise
        except OSError as exc:
            raise _error(f"could not hash gallery artifact {relative}") from exc
        if size != entry["bytes"] or digest != entry["sha256"]:
            raise _error(f"gallery artifact hash or byte count mismatch: {relative}")
        artifact_data[relative] = data

    profiles = manifest["profiles"]
    if not isinstance(profiles, list) or len(profiles) != 4:
        raise _error("gallery manifest must contain exactly four profiles")
    by_id: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(profiles):
        profile_id = PROFILE_IDS[index]
        where = f"gallery manifest.profiles[{index}]"
        _require_fields(raw, {"id", "label", "bridge_manifest_sha256", "bridge_json_sha256", "neutral_source_sha256", "neutral_source_bytes", "structure_source_sha256", "structure_source_bytes", "generated_source_path", "generated_source_sha256", "generated_source_bytes", "candidate_profile_sha256", "source", "gallery", "artifacts", "metrics"}, where)
        if raw["id"] != profile_id or raw["label"] != PROFILE_LABEL_BY_ID[profile_id] or profile_id in by_id:
            raise _error("gallery profile IDs or candidate-table labels are not exact")
        if raw["candidate_profile_sha256"] != PROFILE_SHA256[profile_id]:
            raise _error(f"{where}.candidate_profile_sha256 is not frozen")
        for key in ("bridge_manifest_sha256", "bridge_json_sha256", "neutral_source_sha256", "structure_source_sha256"):
            _hash(raw[key], f"{where}.{key}")
        for key in ("neutral_source_bytes", "structure_source_bytes"):
            if isinstance(raw[key], bool) or not isinstance(raw[key], int) or raw[key] < 0:
                raise _error(f"{where}.{key} is invalid")
        generated_source_path = _safe_relative(raw["generated_source_path"], f"{where}.generated_source_path")
        if generated_source_path != f"{SOURCES_DIR}/{profile_id}.json":
            raise _error(f"{where}.generated_source_path is not source-bound")
        generated_source_sha256 = _hash(raw["generated_source_sha256"], f"{where}.generated_source_sha256")
        generated_source_bytes = raw["generated_source_bytes"]
        if isinstance(generated_source_bytes, bool) or not isinstance(generated_source_bytes, int) or generated_source_bytes < 0 or generated_source_bytes > MAX_FILE_BYTES:
            raise _error(f"{where}.generated_source_bytes is invalid")
        if inventory_by_path[generated_source_path] != {
            "path": generated_source_path,
            "sha256": generated_source_sha256,
            "bytes": generated_source_bytes,
        }:
            raise _error(f"{where} generated source does not match its copied inventory entry")
        _require_fields(raw["source"], {"document", "namespace", "candidate_sha256", "request_sha256"}, f"{where}.source")
        expected_source_document = f"{FROZEN_BASE_SOURCE_DOCUMENT}__structural_profile__{profile_id}"
        if raw["source"]["document"] != expected_source_document or raw["source"]["namespace"] != FROZEN_BASE_SOURCE_NAMESPACE:
            raise _error(f"{where}.source identity is not source-bound")
        _hash(raw["source"]["candidate_sha256"], f"{where}.source.candidate_sha256")
        _hash(raw["source"]["request_sha256"], f"{where}.source.request_sha256")
        _require_fields(raw["gallery"], {"path", "global_world_bound"}, f"{where}.gallery")
        if raw["gallery"]["path"] != f"{profile_id}/{GALLERY_FILE}":
            raise _error(f"{where}.gallery.path is invalid")
        profile_artifacts = raw["artifacts"]
        if not isinstance(profile_artifacts, list) or [item.get("path") if isinstance(item, dict) else None for item in profile_artifacts] != [f"{profile_id}/{name}" for name in PROFILE_ARTIFACT_NAMES]:
            raise _error(f"{where}.artifacts are not in exact order")
        for item_index, item in enumerate(profile_artifacts):
            normalized = _artifact_entry(item, f"{where}.artifacts[{item_index}]")
            if normalized != inventory_by_path[normalized["path"]]:
                raise _error(f"{where}.artifacts[{item_index}] disagrees with root inventory")
        if not isinstance(raw["metrics"], dict) or raw["metrics"].get("format") != GALLERY_FORMAT or raw["metrics"].get("profile_id") != profile_id:
            raise _error(f"{where}.metrics is not a valid profile metrics record")
        _require_fields(raw["metrics"], {"format", "profile_id", "neutral_vertex_count", "posed_vertex_count", "face_count", "bone_count", "proxy_count", "neutral_bounds", "posed_bounds", "pose_rule_count", "source_joint_frame_policy", "gallery_global_world_bound"}, f"{where}.metrics")
        if raw["metrics"]["source_joint_frame_policy"] != "identity-only-validated-from-hash-bound-structure" or raw["metrics"]["gallery_global_world_bound"] != manifest["global_world_bound"]:
            raise _error(f"{where}.metrics lineage is invalid")
        for key in ("neutral_vertex_count", "posed_vertex_count", "face_count", "bone_count", "proxy_count", "pose_rule_count"):
            if isinstance(raw["metrics"][key], bool) or not isinstance(raw["metrics"][key], int) or raw["metrics"][key] < 0:
                raise _error(f"{where}.metrics.{key} is invalid")
        if raw["gallery"]["global_world_bound"] != manifest["global_world_bound"]:
            raise _error(f"{where}.gallery lineage is invalid")
        by_id[profile_id] = raw

    image_hashes: set[str] = set()
    for profile_id in PROFILE_IDS:
        relative = f"{profile_id}/{GALLERY_FILE}"
        digest = inventory_by_path[relative]["sha256"]
        if digest in image_hashes:
            raise _error("profile gallery PNGs must have distinct image hashes")
        image_hashes.add(digest)
        _validate_png(artifact_data[relative], f"{profile_id} gallery PNG")

    pose = _validate_pose_bytes(artifact_data[POSE_FILE])
    prepared_profiles: list[dict[str, Any]] = []
    for profile_id in PROFILE_IDS:
        source_data = artifact_data[f"{SOURCES_DIR}/{profile_id}.json"]
        try:
            source = _source_semantic_inputs(source_data, profile_id)
            prepared_profiles.append(_validate_profile_semantics(profile_id, by_id[profile_id], artifact_data, source, pose))
        except gallery_generator.GalleryError as exc:
            raise _error(f"{profile_id} source semantic evidence is invalid: {exc}") from exc
    try:
        lower, upper = gallery_generator._bounds(gallery_generator._all_bound_points(prepared_profiles))
    except gallery_generator.GalleryError as exc:
        raise _error(f"gallery global world bound cannot be recomputed: {exc}") from exc
    expected_global_bound = {"min": list(lower), "max": list(upper)}
    if manifest["global_world_bound"] != expected_global_bound:
        raise _error("gallery global world bound is not consistent with all validated profiles")
    for profile_id, prepared in zip(PROFILE_IDS, prepared_profiles):
        try:
            expected_gallery = gallery_generator._render_gallery(
                {**prepared, "label": PROFILE_LABEL_BY_ID[profile_id]},
                (lower, upper),
            )
        except gallery_generator.GalleryError as exc:
            raise _error(f"{profile_id} gallery PNG cannot be reproduced from validated evidence: {exc}") from exc
        if artifact_data[f"{profile_id}/{GALLERY_FILE}"] != expected_gallery:
            raise _error(f"{profile_id} gallery PNG is not the deterministic render of the validated evidence")
    return manifest, by_id, hashlib.sha256(manifest_bytes).hexdigest(), len(manifest_bytes)


def _build_review_manifest(gallery: Path, manifest: dict[str, Any], profiles: dict[str, dict[str, Any]], manifest_hash: str, manifest_bytes: int) -> dict[str, Any]:
    items = []
    for profile_id in PROFILE_IDS:
        profile = profiles[profile_id]
        image_path = (gallery / profile_id / GALLERY_FILE).absolute()
        artifact = next(item for item in manifest["artifacts"] if item["path"] == f"{profile_id}/{GALLERY_FILE}")
        items.append({
            "id": profile_id,
            "title": profile["label"],
            "source": str(image_path),
            "description": f"Generated {profile['label']} structural gallery.",
            "metadata": {
                "profile_id": profile_id,
                "profile_label": profile["label"],
                "artifact": {**artifact, **CANVAS},
                "build": manifest["lineage"]["build"],
                "scenario": manifest["lineage"]["scenario"],
                "lineage": {
                    "gallery_manifest_sha256": manifest_hash,
                    "candidate_profile_sha256": profile["candidate_profile_sha256"],
                },
                "generator_reported_upstream_lineage": {
                    "bridge_manifest_sha256": profile["bridge_manifest_sha256"],
                    "bridge_json_sha256": profile["bridge_json_sha256"],
                    "neutral_source_sha256": profile["neutral_source_sha256"],
                    "neutral_source_bytes": profile["neutral_source_bytes"],
                    "structure_source_sha256": profile["structure_source_sha256"],
                    "structure_source_bytes": profile["structure_source_bytes"],
                    "generated_source_path": profile["generated_source_path"],
                    "generated_source_sha256": profile["generated_source_sha256"],
                    "generated_source_bytes": profile["generated_source_bytes"],
                    "source": profile["source"],
                },
            },
        })
    return {
        "schema_version": 1,
        "id": "shared-pose-structural-embodiment-gallery",
        "title": TITLE,
        "description": DESCRIPTION,
        "instructions": INSTRUCTIONS,
        "kind": "image",
        "subject_context": {
            "authored_summary": {"text": "Four generated structural-embodiment profiles from one shared deterministic pose scenario."},
            "descriptor_snapshot": {
                "gallery_manifest_sha256": manifest_hash,
                "gallery_manifest_bytes": manifest_bytes,
                "profile_ids": list(PROFILE_IDS),
                "canvas": CANVAS,
                "pose_id": manifest["pose_id"],
                "pose_sha256": manifest["pose_sha256"],
                "candidate_table_sha256": manifest["candidate_table"]["sha256"],
            },
            "provenance": manifest["lineage"],
        },
        "groups": [{"id": "structural_profiles", "title": "Frozen structural profiles", "selection_mode": "none", "items": items}],
    }


def publish_structural_embodiment(reviews_root: Path, gallery: Path, *, review_id: str | None = None) -> dict[str, Any]:
    """Validate one completed gallery and publish only its four PNGs."""
    gallery = gallery.absolute()
    stable_id = review_id or "shared-pose-structural-embodiment-gallery"
    try:
        stable_id = validate_id(stable_id, "review id")
    except ValidationError as exc:
        raise StructuralEmbodimentPublishError(str(exc)) from exc
    try:
        manifest, profiles, manifest_hash, manifest_bytes = validate_structural_embodiment_gallery(gallery)
        review = _build_review_manifest(gallery, manifest, profiles, manifest_hash, manifest_bytes)
        expected_sources = {
            item["id"]: {
                "bytes": item["metadata"]["artifact"]["bytes"],
                "sha256": item["metadata"]["artifact"]["sha256"],
            }
            for group in review["groups"]
            for item in group["items"]
        }
        with tempfile.TemporaryDirectory(prefix="ck-structural-embodiment-review-") as temporary:
            manifest_path = Path(temporary) / "manifest.json"
            manifest_path.write_text(canonical_json({**review, "id": stable_id}), encoding="utf-8")
            try:
                summary = publish_session(reviews_root, manifest_path, expected_sources=expected_sources)
            except (ValidationError, PublishError, OSError) as exc:
                raise StructuralEmbodimentPublishError(f"could not publish structural embodiment review: {exc}") from exc
    except StructuralEmbodimentPublishError:
        raise
    except (OSError, ValueError) as exc:
        raise StructuralEmbodimentPublishError(str(exc)) from exc
    return {**summary, "kind": "image"}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path, help="existing reviews root")
    parser.add_argument("--gallery", required=True, type=Path, help="completed structural gallery directory")
    parser.add_argument("--id", dest="review_id", help="stable review/session ID")
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        summary = publish_structural_embodiment(args.root, args.gallery, review_id=args.review_id)
    except StructuralEmbodimentPublishError as exc:
        print(f"publish failed: {exc}", file=sys.stderr)
        return 2
    print(canonical_json(summary), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

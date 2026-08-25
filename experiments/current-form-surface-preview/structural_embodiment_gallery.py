#!/usr/bin/env python3
"""Build the bounded shared-pose structural embodiment gallery.

This is a disposable consumer of four already-successful structural bridge
bundles.  The bridge remains authoritative for source ownership and weights;
this module only validates its published evidence, applies one explicit local
pose, performs rigid bind/skin transforms and classic linear blend skinning,
and publishes derived evidence atomically.

All matrices use row-major storage but column vectors:

    p_world = M @ [x, y, z, 1]
    M_parent_child = inverse(M_parent_world) @ M_child_world
    M_skin = M_posed_world @ inverse(M_bind_world)

No runtime, engine, IK, contact, anatomy, muscle or VR semantics are present.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import stat
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

from PIL import Image, ImageDraw

try:  # Direct module execution puts this directory on sys.path.
    import generate_structural_profile_sources as profile_source_generator
    import structural_atomic_publish
    import structural_embodiment_bridge as bridge
except ImportError:  # pragma: no cover - package import path
    from . import generate_structural_profile_sources as profile_source_generator
    from . import structural_atomic_publish
    from . import structural_embodiment_bridge as bridge


GALLERY_FORMAT = "creature-kernel.disposable-structural-embodiment-gallery.v1"
MANIFEST_FORMAT = "creature-kernel.disposable-structural-embodiment-gallery-manifest.v1"
POSE_FORMAT = "creature-kernel.disposable-structural-embodiment-shared-pose.v1"
POSE_FILE = "structural_embodiment_shared_pose.json"
MANIFEST_FILE = "structural-embodiment-gallery-manifest.json"
GALLERY_FILE = "structural-embodiment-gallery.png"
NEUTRAL_FILE = "neutral.ply"
POSED_FILE = "posed.ply"
SKELETON_FILE = "skeleton.json"
WEIGHTS_FILE = "weights.json"
NEUTRAL_PROXIES_FILE = "proxies-neutral.json"
POSED_PROXIES_FILE = "proxies-posed.json"
METRICS_FILE = "metrics.json"
CANDIDATE_FILE = "structural_profile_candidates.json"
SOURCES_DIR = "sources"
SOURCE_MANIFEST_FILE = "manifest.json"
SOURCE_MANIFEST_FORMAT = "creature-kernel.disposable-structural-profile-source-manifest.v1"
FROZEN_CANDIDATE_TABLE_SHA256 = "68d6e808a21daad16e1d56716124fc96b021bc492adf5171ec4e155591f45336"

FROZEN_PROFILE_IDS = (
    "compact_broad_short_limb_large_head",
    "tall_narrow_long_legged",
    "slender_long_limb",
    "stocky_broad_chested",
)
POSE_RECIPE: dict[tuple[str, str, tuple[str, ...]], tuple[str, float]] = {
    ("synthetic-root", "", ()): ("identity", 0.0),
    ("joint", "spine", ()): ("identity", 0.0),
    ("joint", "neck_base", ()): ("x", 2.0),
    ("joint", "head_base", ()): ("x", 2.0),
    ("joint", "shoulder", ("left",)): ("z", 6.0),
    ("joint", "shoulder", ("right",)): ("z", -6.0),
    ("joint", "elbow", ("left",)): ("z", -8.0),
    ("joint", "elbow", ("right",)): ("z", 8.0),
    ("joint", "wrist", ("left",)): ("identity", 0.0),
    ("joint", "wrist", ("right",)): ("identity", 0.0),
    ("joint", "hip", ("left",)): ("z", 5.0),
    ("joint", "hip", ("right",)): ("z", -5.0),
    ("joint", "knee", ("left",)): ("z", -6.0),
    ("joint", "knee", ("right",)): ("z", 6.0),
    ("joint", "ankle", ("left",)): ("identity", 0.0),
    ("joint", "ankle", ("right",)): ("identity", 0.0),
    ("joint", "base", ("tail",)): ("x", 4.0),
    ("joint", "segment", ("tail",)): ("x", 4.0),
}
NEUTRAL_VARIANT_ID = "neutral-v0"
MAX_JSON_BYTES = 16 * 1024 * 1024
MAX_JSON_NODES = 800_000
MAX_JSON_DEPTH = 96
MAX_STRING_LENGTH = 65_536
MAX_PROFILES = 4
MAX_ARTIFACT_BYTES = 32 * 1024 * 1024
MAX_TOTAL_OUTPUT_BYTES = 128 * 1024 * 1024
MAX_OUTPUT_ARTIFACTS = 64
MAX_RENDER_FACES = 40_000
MAX_RENDER_VERTICES = 100_000
CANVAS = (1800, 2500)
PANEL_WIDTH = 600
PANEL_HEIGHT = 500
DECIMAL_PLACES = 12
EPSILON = 1.0e-12
CAPSULE_ARC_STEPS = 24
THREE_QUARTER_DEPTH_FACTOR = 0.65
THREE_QUARTER_BASIS_NORM = math.sqrt(1.0 + THREE_QUARTER_DEPTH_FACTOR**2)


class GalleryError(ValueError):
    """A bounded, fail-closed gallery validation or publication failure."""


@dataclass(frozen=True)
class ProfileInput:
    """One bridge output and the neutral PLY named by its bridge inventory."""

    bridge_dir: Path
    neutral_ply: Path
    inspect_structure: Path


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise GalleryError("value cannot be encoded as canonical finite JSON") from exc


def _output_json(value: Any) -> bytes:
    return _canonical(value) + b"\n"


def _finite_json(value: Any, where: str = "json", *, depth: int = 0, state: list[int] | None = None) -> None:
    if state is None:
        state = [0]
    state[0] += 1
    if state[0] > MAX_JSON_NODES:
        raise GalleryError(f"{where} exceeds the bounded JSON node count")
    if depth > MAX_JSON_DEPTH:
        raise GalleryError(f"{where} exceeds the bounded JSON depth")
    if isinstance(value, float):
        if not math.isfinite(value):
            raise GalleryError(f"{where} contains a non-finite number")
        return
    if isinstance(value, int) and not isinstance(value, bool):
        if abs(value) > 10**15:
            raise GalleryError(f"{where} contains an unbounded integer")
        return
    if isinstance(value, str):
        if len(value) > MAX_STRING_LENGTH:
            raise GalleryError(f"{where} contains an overlong string")
        return
    if isinstance(value, list):
        if len(value) > MAX_JSON_NODES:
            raise GalleryError(f"{where} contains an oversized array")
        for index, item in enumerate(value):
            _finite_json(item, f"{where}[{index}]", depth=depth + 1, state=state)
        return
    if isinstance(value, dict):
        if len(value) > 2048:
            raise GalleryError(f"{where} contains an oversized object")
        for key, item in value.items():
            if not isinstance(key, str) or len(key) > MAX_STRING_LENGTH:
                raise GalleryError(f"{where} contains an invalid object key")
            _finite_json(item, f"{where}.{key}", depth=depth + 1, state=state)
        return
    if value is not None and not isinstance(value, bool):
        raise GalleryError(f"{where} contains an unsupported JSON value")


def _reject_symlink_components(path: Path, where: str) -> None:
    """Reject existing symlinks in the lexical path without resolving it."""
    try:
        absolute = Path(os.path.abspath(os.fspath(path)))
    except (OSError, TypeError, ValueError) as exc:
        raise GalleryError(f"{where} is not a usable lexical path") from exc
    current = Path(absolute.anchor)
    for component in absolute.parts[1:]:
        current /= component
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            return
        except OSError as exc:
            raise GalleryError(f"could not inspect {where} path components") from exc
        if stat.S_ISLNK(mode):
            raise GalleryError(f"{where} contains a symlinked path component")


def _regular_file(path: Path, where: str) -> None:
    _reject_symlink_components(path, where)
    try:
        info = path.lstat()
    except OSError as exc:
        raise GalleryError(f"{where} is unavailable") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise GalleryError(f"{where} must be a regular non-symlink file")


def _directory(path: Path, where: str) -> None:
    _reject_symlink_components(path, where)
    try:
        info = path.lstat()
    except OSError as exc:
        raise GalleryError(f"{where} is unavailable") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise GalleryError(f"{where} must be a regular non-symlink directory")


def _directory_identity(path: Path, where: str) -> tuple[int, int]:
    """Return the selected regular directory identity before opening it."""
    _directory(path, where)
    try:
        info = path.lstat()
    except OSError as exc:
        raise GalleryError(f"{where} is unavailable") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise GalleryError(f"{where} must be a regular non-symlink directory")
    return info.st_dev, info.st_ino


def _load_json(path: Path, where: str) -> tuple[Any, bytes]:
    _regular_file(path, where)
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise GalleryError(f"could not read {where}") from exc
    if len(data) > MAX_JSON_BYTES:
        raise GalleryError(f"{where} exceeds the bounded JSON size")
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise GalleryError(f"{where} is not valid finite UTF-8 JSON") from exc
    _finite_json(value, where)
    return value, data


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _obj(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise GalleryError(f"{where} must be an object")
    return value


def _text(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value or len(value) > MAX_STRING_LENGTH:
        raise GalleryError(f"{where} must be a bounded non-empty string")
    return value


def _vector(value: Any, where: str, length: int = 3) -> tuple[float, ...]:
    if not isinstance(value, list) or len(value) != length:
        raise GalleryError(f"{where} must be a finite {length}-vector")
    result = []
    for index, item in enumerate(value):
        if isinstance(item, bool) or not isinstance(item, (int, float)) or not math.isfinite(float(item)):
            raise GalleryError(f"{where}[{index}] must be finite numeric data")
        result.append(float(item))
    return tuple(result)


def _safe_relative(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise GalleryError(f"{where} is not a safe relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts) or str(path) != value:
        raise GalleryError(f"{where} contains path traversal")
    return value


def _hash_file(path: Path, where: str, maximum: int = MAX_ARTIFACT_BYTES) -> tuple[str, int, bytes]:
    _regular_file(path, where)
    digest = hashlib.sha256()
    size = 0
    chunks: list[bytes] = []
    try:
        with path.open("rb") as stream:
            while True:
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > maximum:
                    raise GalleryError(f"{where} exceeds the bounded artifact size")
                digest.update(chunk)
                chunks.append(chunk)
    except OSError as exc:
        raise GalleryError(f"could not hash {where}") from exc
    return digest.hexdigest(), size, b"".join(chunks)


def _scan_tree(root: Path) -> tuple[set[str], set[str]]:
    files: set[str] = set()
    directories: set[str] = set()
    count = 0

    def walk(directory: Path, relative: str) -> None:
        nonlocal count
        try:
            entries = sorted(os.scandir(directory), key=lambda entry: entry.name)
        except OSError as exc:
            raise GalleryError("could not scan gallery tree") from exc
        for entry in entries:
            count += 1
            if count > 2048:
                raise GalleryError("gallery tree has too many entries")
            name = entry.name
            if name in {"", ".", ".."} or "/" in name or "\\" in name:
                raise GalleryError("gallery tree contains an unsafe entry name")
            child_relative = f"{relative}/{name}" if relative else name
            try:
                info = entry.stat(follow_symlinks=False)
            except OSError as exc:
                raise GalleryError("could not stat gallery tree member") from exc
            if stat.S_ISLNK(info.st_mode):
                raise GalleryError(f"gallery tree contains a symlink: {child_relative}")
            if stat.S_ISDIR(info.st_mode):
                directories.add(child_relative)
                walk(Path(entry.path), child_relative)
            elif stat.S_ISREG(info.st_mode):
                files.add(child_relative)
            else:
                raise GalleryError(f"gallery tree contains a special file: {child_relative}")

    walk(root, "")
    return files, directories


def _require_fields(value: Mapping[str, Any], required: Iterable[str], where: str) -> None:
    expected = set(required)
    if set(value) != expected:
        missing = sorted(expected - set(value))
        extra = sorted(set(value) - expected)
        detail = []
        if missing:
            detail.append("missing " + ", ".join(missing))
        if extra:
            detail.append("unknown " + ", ".join(extra))
        raise GalleryError(f"{where} has invalid fields ({'; '.join(detail)})")


def _load_candidates(path: Path) -> dict[str, Any]:
    value, data = _load_json(path, "structural profile candidate table")
    root = _obj(value, "structural profile candidate table")
    _require_fields(root, ("base_source", "canonicalization", "format", "profiles", "transform"), "candidate table")
    if root["format"] != "creature-kernel.disposable-structural-profile-candidates.v1":
        raise GalleryError("candidate table format is unsupported")
    profiles = root["profiles"]
    if not isinstance(profiles, list) or len(profiles) != MAX_PROFILES:
        raise GalleryError("candidate table must contain exactly four profiles")
    ids: list[str] = []
    by_id: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(profiles):
        item = _obj(raw, f"candidate table.profiles[{index}]")
        if set(item) != {"dimension_scales", "id", "label", "part_placements"}:
            raise GalleryError("candidate table profile has invalid fields")
        profile_id = _text(item["id"], f"candidate profile[{index}].id")
        if profile_id in by_id:
            raise GalleryError("candidate table contains duplicate profile IDs")
        ids.append(profile_id)
        by_id[profile_id] = item
    if tuple(ids) != FROZEN_PROFILE_IDS:
        raise GalleryError("candidate table IDs are not the exact frozen four-profile set")
    digest = hashlib.sha256(data).hexdigest()
    if digest != FROZEN_CANDIDATE_TABLE_SHA256:
        raise GalleryError("candidate table bytes are not the exact frozen structural candidate table")
    return {
        "root": root,
        "profiles": by_id,
        "sha256": digest,
        "bytes": len(data),
        "data": data,
    }


def _records_by_address(records: Any, where: str) -> dict[tuple[str, tuple[str, ...], str, str], dict[str, Any]]:
    if not isinstance(records, list):
        raise GalleryError(f"{where} must be an array")
    result: dict[tuple[str, tuple[str, ...], str, str], dict[str, Any]] = {}
    for index, raw in enumerate(records):
        item = _obj(raw, f"{where}[{index}]")
        key = _address_key(item.get("address"), f"{where}[{index}].address")
        if key in result:
            raise GalleryError(f"{where} contains duplicate addresses")
        result[key] = item
    return result


def _expected_source_documents(candidate_table: dict[str, Any]) -> dict[str, bytes]:
    """Regenerate exact source bytes from the frozen table and hashed base."""
    candidate_root = candidate_table["root"]
    base_source = _obj(candidate_root.get("base_source"), "candidate table.base_source")
    _require_fields(base_source, ("document", "namespace", "path", "sha256"), "candidate table.base_source")
    relative = _safe_relative(base_source["path"], "candidate table.base_source.path")
    repository_root = Path(__file__).resolve().parents[2]
    source_path = repository_root / relative
    source_value, source_data = _load_json(source_path, "frozen base source")
    if hashlib.sha256(source_data).hexdigest() != base_source["sha256"]:
        raise GalleryError("frozen base source bytes do not match the candidate table")
    try:
        outputs = profile_source_generator.generate_sources(candidate_root, source_value)
        expected = {
            profile_id: profile_source_generator.canonical_source_bytes(output)
            for profile_id, output in zip(FROZEN_PROFILE_IDS, outputs)
        }
    except profile_source_generator.ProfileGenerationError as exc:
        raise GalleryError("could not reproduce generated sources from the frozen candidate table") from exc
    if set(expected) != set(FROZEN_PROFILE_IDS):
        raise GalleryError("frozen candidate regeneration did not produce the exact four-profile set")
    return expected


def _load_source_manifest(path: Path, candidate_table: dict[str, Any]) -> dict[str, Any]:
    """Load the exact generated four-source set that binds profiles to the table."""
    if path.name != SOURCE_MANIFEST_FILE:
        raise GalleryError("source manifest must be named manifest.json")
    root_dir = path.parent
    _directory(root_dir, "generated source root")
    files, directories = _scan_tree(root_dir)
    expected_files = {SOURCE_MANIFEST_FILE, *(f"{profile_id}.json" for profile_id in FROZEN_PROFILE_IDS)}
    if files != expected_files or directories:
        raise GalleryError("generated source root must contain exactly manifest.json and the four profile sources")
    value, manifest_data = _load_json(path, "generated source manifest")
    manifest = _obj(value, "generated source manifest")
    _require_fields(manifest, ("candidate_format", "format", "profiles", "source"), "generated source manifest")
    candidate_root = candidate_table["root"]
    if manifest["format"] != SOURCE_MANIFEST_FORMAT or manifest["candidate_format"] != candidate_root["format"]:
        raise GalleryError("generated source manifest format is unsupported")
    source = _obj(manifest["source"], "generated source manifest.source")
    _require_fields(source, ("base_document", "base_namespace", "candidate_sha256", "source_sha256"), "generated source manifest.source")
    base_source = _obj(candidate_root["base_source"], "candidate table.base_source")
    if source != {
        "base_document": base_source["document"],
        "base_namespace": base_source["namespace"],
        "candidate_sha256": candidate_table["sha256"],
        "source_sha256": base_source["sha256"],
    }:
        raise GalleryError("generated source manifest does not bind the exact candidate table and base source")
    expected_source_data = _expected_source_documents(candidate_table)
    profiles = manifest["profiles"]
    if not isinstance(profiles, list) or [item.get("id") if isinstance(item, dict) else None for item in profiles] != list(FROZEN_PROFILE_IDS):
        raise GalleryError("generated source manifest profile order is not the frozen order")
    by_id: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(profiles):
        profile_id = FROZEN_PROFILE_IDS[index]
        record = _obj(raw, f"generated source manifest.profiles[{index}]")
        _require_fields(record, ("bytes", "document", "file", "id", "sha256", "tail_signature"), f"generated source manifest.profiles[{index}]")
        expected_document = f"{base_source['document']}__structural_profile__{profile_id}"
        if record["id"] != profile_id or record["file"] != f"{profile_id}.json" or record["document"] != expected_document:
            raise GalleryError("generated source manifest profile identity is invalid")
        if type(record["bytes"]) is not int or record["bytes"] <= 0 or record["bytes"] > MAX_ARTIFACT_BYTES:
            raise GalleryError("generated source manifest byte count is invalid")
        if not isinstance(record["sha256"], str) or len(record["sha256"]) != 64 or any(char not in "0123456789abcdef" for char in record["sha256"]):
            raise GalleryError("generated source manifest hash is invalid")
        source_path = root_dir / record["file"]
        source_hash, source_bytes, source_data = _hash_file(source_path, f"generated source {profile_id}")
        if source_hash != record["sha256"] or source_bytes != record["bytes"]:
            raise GalleryError(f"generated source {profile_id} does not match its manifest")
        if source_data != expected_source_data[profile_id]:
            raise GalleryError(f"generated source {profile_id} is not the exact output of the frozen candidate table")
        source_value, reread = _load_json(source_path, f"generated source {profile_id}")
        if reread != source_data:
            raise GalleryError(f"generated source {profile_id} changed during validation")
        source_root = _obj(source_value, f"generated source {profile_id}")
        source_identity = _obj(source_root.get("source"), f"generated source {profile_id}.source")
        body = _obj(source_root.get("body"), f"generated source {profile_id}.body")
        if source_identity.get("document") != expected_document or source_identity.get("namespace") != base_source["namespace"]:
            raise GalleryError(f"generated source {profile_id} identity is invalid")
        parts = _records_by_address(body.get("parts"), f"generated source {profile_id}.body.parts")
        joints = _records_by_address(body.get("joints"), f"generated source {profile_id}.body.joints")
        if len(parts) != 18 or len(joints) != 17:
            raise GalleryError(f"generated source {profile_id} does not have the exact structural inventory")
        by_id[profile_id] = {
            "record": record,
            "root": source_root,
            "parts": parts,
            "joints": joints,
            "data": source_data,
        }
    return {
        "manifest": manifest,
        "manifest_data": manifest_data,
        "manifest_sha256": hashlib.sha256(manifest_data).hexdigest(),
        "manifest_bytes": len(manifest_data),
        "profiles": by_id,
    }


def _candidate_profile_identity(candidate_table: dict[str, Any], profile_id: str) -> str:
    profile = candidate_table["profiles"].get(profile_id)
    if profile is None:
        raise GalleryError(f"{profile_id} is absent from the frozen candidate table")
    # This digest is the identity of the exact loaded profile record, not an
    # inferred or re-serialized source document identity.
    return hashlib.sha256(_canonical(profile)).hexdigest()


def _identity_frame(frame: Any, where: str) -> None:
    item = _obj(frame, where)
    _require_fields(item, ("translation", "rotation_xyzw"), where)
    translation = _vector(item["translation"], f"{where}.translation")
    rotation = _vector(item["rotation_xyzw"], f"{where}.rotation_xyzw", 4)
    if any(abs(item) > EPSILON for item in translation) or any(
        abs(item - expected) > EPSILON for item, expected in zip(rotation, (0.0, 0.0, 0.0, 1.0))
    ):
        raise GalleryError("non-identity source Joint frame/rotation is unsupported by the shared pose")


def _validate_structure_frames(path: Path, expected_hash: str) -> dict[str, Any]:
    value, data = _load_json(path, "hash-bound inspect-structure JSON")
    if hashlib.sha256(data).hexdigest() != expected_hash:
        raise GalleryError("inspect-structure JSON does not match bridge inventory hash")
    bridge._validate_structure(value)
    root = _obj(value, "hash-bound inspect-structure JSON")
    graph = _obj(root.get("graph"), "hash-bound inspect-structure graph")
    joints = graph.get("joints")
    if not isinstance(joints, list) or not joints:
        raise GalleryError("hash-bound inspect-structure JSON has no semantic Joints")
    # bridge._validate_structure intentionally returns a compact graph and
    # does not retain frame payloads. Inspect the already hash-bound raw graph
    # here so source frame semantics cannot be silently lost at this boundary.
    for index, raw_joint in enumerate(joints):
        joint = _obj(raw_joint, f"source Joint[{index}]")
        _identity_frame(joint.get("proximal_frame"), f"source Joint[{index}].proximal_frame")
        _identity_frame(joint.get("distal_frame"), f"source Joint[{index}].distal_frame")
    return graph


def _structure_world_points(
    parts: dict[tuple[str, tuple[str, ...], str, str], dict[str, Any]],
) -> tuple[
    dict[tuple[str, tuple[str, ...], str, str], tuple[float, float, float]],
    tuple[str, tuple[str, ...], str, str],
]:
    """Resolve the checkpoint's identity-rotation Part placements to world points."""
    parents: dict[
        tuple[str, tuple[str, ...], str, str],
        tuple[str, tuple[str, ...], str, str] | None,
    ] = {}
    translations: dict[tuple[str, tuple[str, ...], str, str], tuple[float, float, float]] = {}
    for key, part in parts.items():
        containment = _obj(part.get("containment"), "structure Part containment")
        if set(containment) == {"root"} and containment["root"] is True:
            parent = None
        elif set(containment) == {"parent"}:
            parent = _address_key(containment["parent"], "structure Part parent")
            if parent not in parts:
                raise GalleryError("structure Part parent is absent")
        else:
            raise GalleryError("structure Part containment is invalid")
        placement = _obj(part.get("placement"), "structure Part placement")
        _require_fields(placement, ("rotation_xyzw", "translation"), "structure Part placement")
        rotation = _vector(placement["rotation_xyzw"], "structure Part rotation", 4)
        if rotation != (0.0, 0.0, 0.0, 1.0):
            raise GalleryError("non-identity source Part rotation is unsupported by the shared pose")
        parents[key] = parent
        translations[key] = _vector(placement["translation"], "structure Part translation")  # type: ignore[assignment]
    roots = [key for key, parent in parents.items() if parent is None]
    if len(roots) != 1:
        raise GalleryError("structure Parts do not have exactly one root")
    world: dict[tuple[str, tuple[str, ...], str, str], tuple[float, float, float]] = {}

    def resolve(
        key: tuple[str, tuple[str, ...], str, str],
        trail: set[tuple[str, tuple[str, ...], str, str]],
    ) -> tuple[float, float, float]:
        if key in world:
            return world[key]
        if key in trail:
            raise GalleryError("structure Part containment is cyclic")
        trail.add(key)
        parent = parents[key]
        local = translations[key]
        point = local if parent is None else tuple(
            resolve(parent, trail)[axis] + local[axis] for axis in range(3)
        )
        trail.remove(key)
        world[key] = point
        return point

    for key in parts:
        resolve(key, set())
    return world, roots[0]


def _address_key(address: Any, where: str) -> tuple[str, tuple[str, ...], str, str]:
    key, _ = bridge._address(address, where)
    return key


def _validate_bridge(
    profile_id: str,
    input_record: ProfileInput,
    candidate_table: dict[str, Any],
    generated_source: dict[str, Any],
) -> dict[str, Any]:
    bridge_dir = input_record.bridge_dir
    _directory(bridge_dir, f"{profile_id} bridge bundle")
    files, directories = _scan_tree(bridge_dir)
    if files != {bridge.BRIDGE_FILE, bridge.MANIFEST_FILE} or directories:
        raise GalleryError(f"{profile_id} bridge bundle is not the exact two-file bridge output")
    manifest_value, manifest_bytes = _load_json(bridge_dir / bridge.MANIFEST_FILE, f"{profile_id} bridge manifest")
    manifest = _obj(manifest_value, f"{profile_id} bridge manifest")
    _require_fields(
        manifest,
        ("algorithm_revision", "bridge_format", "candidate_profile_id", "candidate_sha256", "configuration_revision", "format", "input_files", "inventory", "request_sha256", "status", "surface_variant_id"),
        f"{profile_id} bridge manifest",
    )
    if (
        manifest["format"] != bridge.MANIFEST_FORMAT
        or manifest["bridge_format"] != bridge.BRIDGE_FORMAT
        or manifest["status"] != "success"
        or manifest["candidate_profile_id"] != profile_id
        or manifest["surface_variant_id"] != NEUTRAL_VARIANT_ID
    ):
        raise GalleryError(f"{profile_id} bridge manifest is not a successful neutral bridge")
    if not isinstance(manifest["candidate_sha256"], str) or len(manifest["candidate_sha256"]) != 64:
        raise GalleryError(f"{profile_id} bridge candidate hash is invalid")
    if not isinstance(manifest["request_sha256"], str) or len(manifest["request_sha256"]) != 64:
        raise GalleryError(f"{profile_id} bridge request hash is invalid")
    inventory = manifest["inventory"]
    if not isinstance(inventory, list) or len(inventory) != 1:
        raise GalleryError(f"{profile_id} bridge inventory must contain exactly bridge JSON")
    inventory_entry = _obj(inventory[0], f"{profile_id} bridge inventory[0]")
    _require_fields(inventory_entry, ("bytes", "kind", "path", "sha256"), f"{profile_id} bridge inventory[0]")
    if inventory_entry["kind"] != "bridge-json" or inventory_entry["path"] != bridge.BRIDGE_FILE:
        raise GalleryError(f"{profile_id} bridge inventory path is invalid")
    bridge_hash, bridge_bytes, bridge_data = _hash_file(bridge_dir / bridge.BRIDGE_FILE, f"{profile_id} bridge JSON")
    if bridge_hash != inventory_entry["sha256"] or bridge_bytes != inventory_entry["bytes"]:
        raise GalleryError(f"{profile_id} bridge JSON hash does not match its manifest")
    candidate_value, candidate_file_bytes = _load_json(bridge_dir / bridge.BRIDGE_FILE, f"{profile_id} bridge JSON")
    if hashlib.sha256(candidate_file_bytes).hexdigest() != bridge_hash:
        raise GalleryError(f"{profile_id} bridge JSON changed during validation")
    candidate = _obj(candidate_value, f"{profile_id} bridge candidate")
    if candidate.get("format") != bridge.BRIDGE_FORMAT or candidate.get("status") != "success":
        raise GalleryError(f"{profile_id} bridge candidate is not successful")
    source = _obj(candidate.get("source"), f"{profile_id} bridge source")
    if source.get("candidate_profile_id") != profile_id or source.get("surface_variant_id") != NEUTRAL_VARIANT_ID:
        raise GalleryError(f"{profile_id} bridge source identity is invalid")
    identity = _obj(candidate.get("identity"), f"{profile_id} bridge identity")
    _require_fields(identity, ("basis", "candidate_sha256", "request_sha256"), f"{profile_id} bridge identity")
    if identity.get("candidate_sha256") != manifest["candidate_sha256"] or identity.get("request_sha256") != manifest["request_sha256"]:
        raise GalleryError(f"{profile_id} bridge identity does not match its manifest")
    checks = _obj(candidate.get("checks"), f"{profile_id} bridge checks")
    required_checks = {
        "rooted_acyclic_hierarchy",
        "spatially_continuous_hierarchy",
        "complete_joint_to_bone_mapping",
        "finite_nonnegative_normalized_weights",
        "full_vertex_coverage",
        "max_four_influences",
        "every_bone_has_positive_influence",
        "complete_proxy_vertex_partition",
        "finite_non_degenerate_capsules",
    }
    if set(checks) != required_checks or not all(value is True for value in checks.values()):
        raise GalleryError(f"{profile_id} bridge objective checks are not all successful")
    input_files = manifest["input_files"]
    if not isinstance(input_files, list) or not input_files:
        raise GalleryError(f"{profile_id} bridge input inventory is empty")
    by_kind: dict[str, list[dict[str, Any]]] = {}
    seen_paths: set[str] = set()
    for index, raw in enumerate(input_files):
        item = _obj(raw, f"{profile_id} bridge input_files[{index}]")
        _require_fields(item, ("bytes", "kind", "path", "sha256"), f"{profile_id} bridge input_files[{index}]")
        kind = _text(item["kind"], f"{profile_id} bridge input kind")
        path = _safe_relative(item["path"], f"{profile_id} bridge input path")
        if path in seen_paths or not isinstance(item["bytes"], int) or item["bytes"] < 0 or item["bytes"] > MAX_ARTIFACT_BYTES:
            raise GalleryError(f"{profile_id} bridge input inventory is invalid")
        seen_paths.add(path)
        if not isinstance(item["sha256"], str) or len(item["sha256"]) != 64 or any(char not in "0123456789abcdef" for char in item["sha256"]):
            raise GalleryError(f"{profile_id} bridge input hash is invalid")
        by_kind.setdefault(kind, []).append(item)
    expected_basis = {
        "algorithm_revision": manifest["algorithm_revision"],
        "configuration_revision": manifest["configuration_revision"],
        "candidate_profile_id": profile_id,
        "surface_variant_id": NEUTRAL_VARIANT_ID,
        "provenance_semantics": "exact bounded input bytes; logically equivalent re-encodings intentionally have distinct identity",
        "input_files": input_files,
    }
    if identity["basis"] != expected_basis:
        raise GalleryError(f"{profile_id} bridge identity basis does not match its manifest inputs")
    if (
        bridge._digest(bridge.IDENTITY_DOMAIN + ":candidate", expected_basis) != manifest["candidate_sha256"]
        or bridge._digest(bridge.IDENTITY_DOMAIN + ":request", expected_basis) != manifest["request_sha256"]
    ):
        raise GalleryError(f"{profile_id} bridge identity hashes are not reproducible")
    neutral_entries = [
        item for item in by_kind.get("successor-ply", [])
        if item["path"] == f"{NEUTRAL_VARIANT_ID}/surface.ply"
    ]
    if len(neutral_entries) != 1:
        raise GalleryError(f"{profile_id} bridge input inventory has no unique neutral PLY hash")
    ply_entry = neutral_entries[0]
    structure_entries = [
        item for item in by_kind.get("inspect-structure", [])
        if item["path"] == "inspect-structure.json"
    ]
    if len(structure_entries) != 1:
        raise GalleryError(f"{profile_id} bridge has no unique inspect-structure inventory entry")
    structure_entry = structure_entries[0]
    structure_graph = _validate_structure_frames(input_record.inspect_structure, structure_entry["sha256"])
    structure_source = _obj(structure_graph.get("source"), f"{profile_id} structure source")
    generated_identity = _obj(generated_source["root"].get("source"), f"{profile_id} generated source identity")
    if (
        source.get("document") != generated_identity.get("document")
        or source.get("namespace") != generated_identity.get("namespace")
        or structure_source.get("document") != generated_identity.get("document")
        or structure_source.get("namespace") != generated_identity.get("namespace")
    ):
        raise GalleryError(f"{profile_id} bridge, structure, and generated source identities disagree")
    structure_parts = _records_by_address(structure_graph.get("parts"), f"{profile_id} structure.parts")
    structure_joints = _records_by_address(structure_graph.get("joints"), f"{profile_id} structure.joints")
    if structure_parts != generated_source["parts"]:
        raise GalleryError(f"{profile_id} structure Parts do not match the generated source")
    if structure_joints != generated_source["joints"]:
        raise GalleryError(f"{profile_id} structure Joints do not match the generated source")
    neutral_hash, neutral_bytes, neutral_data = _hash_file(input_record.neutral_ply, f"{profile_id} neutral PLY", bridge.MAX_PLY_BYTES)
    if neutral_hash != ply_entry["sha256"] or neutral_bytes != ply_entry["bytes"]:
        raise GalleryError(f"{profile_id} neutral PLY does not match bridge inventory")
    neutral = bridge._parse_ply(input_record.neutral_ply, expected_sha256=neutral_hash)
    _validate_candidate_geometry(
        profile_id,
        candidate,
        neutral,
        structure_parts,
        structure_joints,
    )
    return {
        "id": profile_id,
        "label": _text(candidate_table["profiles"][profile_id]["label"], f"{profile_id} candidate label"),
        "candidate": candidate,
        "manifest": manifest,
        "manifest_hash": hashlib.sha256(manifest_bytes).hexdigest(),
        "bridge_hash": bridge_hash,
        "neutral_hash": neutral_hash,
        "neutral_bytes": neutral_bytes,
        "structure_hash": structure_entry["sha256"],
        "structure_bytes": structure_entry["bytes"],
        "generated_source_sha256": generated_source["record"]["sha256"],
        "generated_source_bytes": generated_source["record"]["bytes"],
        "generated_source_path": f"{SOURCES_DIR}/{profile_id}.json",
        "neutral_data": neutral_data,
        "candidate_profile_sha256": _candidate_profile_identity(candidate_table, profile_id),
        "neutral": neutral,
    }


def _validate_candidate_geometry(
    profile_id: str,
    candidate: dict[str, Any],
    neutral: dict[str, Any],
    expected_parts: dict[tuple[str, tuple[str, ...], str, str], dict[str, Any]],
    expected_joints: dict[tuple[str, tuple[str, ...], str, str], dict[str, Any]],
) -> None:
    if len(neutral["vertices"]) > MAX_RENDER_VERTICES or len(neutral["faces"]) > MAX_RENDER_FACES:
        raise GalleryError(f"{profile_id} neutral surface exceeds the bounded gallery render resources")
    hierarchy = _obj(candidate.get("hierarchy"), f"{profile_id}.hierarchy")
    bones = hierarchy.get("bones")
    if not isinstance(bones, list) or len(bones) != 18:
        raise GalleryError(f"{profile_id} bridge must contain the exact 18-bone structural hierarchy")
    by_id: dict[str, dict[str, Any]] = {}
    roots = []
    for index, raw in enumerate(bones):
        bone = _obj(raw, f"{profile_id}.hierarchy.bones[{index}]")
        bone_id = _text(bone.get("id"), f"{profile_id} bone id")
        if bone_id in by_id:
            raise GalleryError(f"{profile_id} hierarchy contains duplicate bone IDs")
        by_id[bone_id] = bone
        parent = bone.get("parent")
        if parent is None:
            roots.append(bone_id)
        elif not isinstance(parent, str):
            raise GalleryError(f"{profile_id} hierarchy parent is invalid")
        a = _vector(bone.get("a"), f"{profile_id} bone {bone_id}.a")
        b = _vector(bone.get("b"), f"{profile_id} bone {bone_id}.b")
        if math.dist(a, b) <= EPSILON:
            raise GalleryError(f"{profile_id} bone {bone_id} is degenerate")
    if roots != ["bone-source-part-root"]:
        raise GalleryError(f"{profile_id} hierarchy must have exactly the synthetic root")
    world_points, root_part = _structure_world_points(expected_parts)
    root_bone = by_id["bone-source-part-root"]
    root_endpoint = world_points[root_part]
    if (
        _address_key(root_bone.get("source_part"), f"{profile_id} root source_part") != root_part
        or _address_key(root_bone.get("owned_part"), f"{profile_id} root owned_part") != root_part
        or _vector(root_bone.get("b"), f"{profile_id} root endpoint") != root_endpoint
    ):
        raise GalleryError(f"{profile_id} synthetic root is not bound to the source root Part")
    neutral_vertices = [tuple(vertex) for vertex in neutral["vertices"]]
    expected_root_start = tuple(
        math.fsum(vertex[axis] for vertex in neutral_vertices) / len(neutral_vertices)
        for axis in range(3)
    )
    if math.dist(expected_root_start, root_endpoint) <= bridge.MIN_SEGMENT_LENGTH:
        expected_root_start = sorted(
            neutral_vertices,
            key=lambda vertex: (
                -sum((vertex[axis] - root_endpoint[axis]) ** 2 for axis in range(3)),
                vertex,
            ),
        )[0]
    root_start = _vector(root_bone.get("a"), f"{profile_id} root surface anchor")
    if (
        root_start != expected_root_start
        or root_bone.get("surface_anchor_rule")
        != "centroid of the complete neutral surface, with lexicographically stable farthest-vertex fallback"
    ):
        raise GalleryError(f"{profile_id} synthetic root surface anchor is not exactly derived from the neutral surface")
    for bone in bones:
        current: str | None = bone["id"]
        seen: set[str] = set()
        while current is not None:
            if current in seen or current not in by_id:
                raise GalleryError(f"{profile_id} hierarchy is cyclic or references an unknown parent")
            seen.add(current)
            current = by_id[current].get("parent")
        parent = bone.get("parent")
        if parent is not None and _vector(by_id[parent].get("b"), f"{profile_id} parent endpoint") != _vector(bone.get("a"), f"{profile_id} child start"):
            raise GalleryError(f"{profile_id} hierarchy is spatially discontinuous")
    mapping = hierarchy.get("joint_address_to_bone")
    if not isinstance(mapping, list) or len(mapping) != 17:
        raise GalleryError(f"{profile_id} joint-to-bone mapping is incomplete")
    mapping_bones: set[str] = set()
    mapping_joints: set[tuple[str, tuple[str, ...], str, str]] = set()
    for index, raw_mapping in enumerate(mapping):
        item = _obj(raw_mapping, f"{profile_id}.joint_address_to_bone[{index}]")
        _require_fields(item, ("bone_id", "joint"), f"{profile_id}.joint_address_to_bone[{index}]")
        bone_id = _text(item["bone_id"], f"{profile_id}.joint_address_to_bone[{index}].bone_id")
        if bone_id not in by_id or bone_id == "bone-source-part-root" or bone_id in mapping_bones:
            raise GalleryError(f"{profile_id} joint-to-bone mapping is incomplete")
        joint_key = _address_key(item["joint"], f"{profile_id}.joint_address_to_bone[{index}].joint")
        if joint_key in mapping_joints or joint_key not in expected_joints:
            raise GalleryError(f"{profile_id} joint-to-bone mapping is not the exact source Joint set")
        bone = by_id[bone_id]
        expected_joint = expected_joints[joint_key]
        if (
            bone.get("joint") != expected_joint.get("address")
            or bone.get("proximal") != expected_joint.get("proximal")
            or bone.get("distal") != expected_joint.get("distal")
        ):
            raise GalleryError(f"{profile_id} mapped bone endpoints do not match the source Joint")
        proximal_key = _address_key(expected_joint["proximal"], f"{profile_id} source Joint proximal")
        distal_key = _address_key(expected_joint["distal"], f"{profile_id} source Joint distal")
        if (
            _vector(bone.get("a"), f"{profile_id} mapped bone start") != world_points[proximal_key]
            or _vector(bone.get("b"), f"{profile_id} mapped bone end") != world_points[distal_key]
            or _address_key(bone.get("owned_part"), f"{profile_id} mapped bone owner") != distal_key
            or [
                _address_key(value, f"{profile_id} mapped bone source_parts")
                for value in bone.get("source_parts", [])
            ] != [proximal_key, distal_key]
        ):
            raise GalleryError(f"{profile_id} mapped bone geometry is not derived from source Part placements")
        mapping_bones.add(bone_id)
        mapping_joints.add(joint_key)
    if mapping_bones != set(by_id) - {"bone-source-part-root"}:
        raise GalleryError(f"{profile_id} joint-to-bone mapping does not cover every derived bone")
    if mapping_joints != set(expected_joints):
        raise GalleryError(f"{profile_id} joint-to-bone mapping does not cover every source Joint")
    weights = _obj(candidate.get("weights"), f"{profile_id}.weights")
    rows = weights.get("influences")
    if weights.get("vertex_count") != len(neutral["vertices"]) or not isinstance(rows, list) or len(rows) != len(neutral["vertices"]):
        raise GalleryError(f"{profile_id} weight count does not match neutral PLY")
    positive_bones: set[str] = set()
    primary_counts: dict[str, int] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, list) or not row or len(row) > 4:
            raise GalleryError(f"{profile_id} weights[{index}] has invalid influence coverage")
        total = 0.0
        row_bones: set[str] = set()
        for influence in row:
            item = _obj(influence, f"{profile_id} weights[{index}] influence")
            bone_id = _text(item.get("bone_id"), "weight bone id")
            weight = item.get("weight")
            if bone_id in row_bones or bone_id not in by_id or isinstance(weight, bool) or not isinstance(weight, (int, float)) or not math.isfinite(float(weight)) or float(weight) < 0.0:
                raise GalleryError(f"{profile_id} weights contain invalid influence data")
            row_bones.add(bone_id)
            if float(weight) > 0.0:
                positive_bones.add(bone_id)
            total += float(weight)
        if not math.isfinite(total) or abs(total - 1.0) > 1.0e-12:
            raise GalleryError(f"{profile_id} weights[{index}] are not normalized")
        primary = min(row, key=lambda item: (-float(item["weight"]), item["bone_id"]))["bone_id"]
        primary_counts[primary] = primary_counts.get(primary, 0) + 1
    if positive_bones != set(by_id):
        raise GalleryError(f"{profile_id} weights do not give every bone positive influence")
    proxies = candidate.get("proxies")
    if not isinstance(proxies, list) or not proxies:
        raise GalleryError(f"{profile_id} has no collision capsules")
    proxy_bones: set[str] = set()
    partition_total = 0
    for proxy in proxies:
        item = _obj(proxy, f"{profile_id} proxy")
        _require_fields(
            item,
            ("a", "b", "bone_id", "kind", "owned_part", "partition_rule", "partition_vertex_count", "radius", "radius_rule"),
            f"{profile_id} proxy",
        )
        if item.get("kind") != "capsule" or item.get("bone_id") not in by_id:
            raise GalleryError(f"{profile_id} proxy is not bound to a bridge bone")
        if item["bone_id"] in proxy_bones:
            raise GalleryError(f"{profile_id} contains duplicate proxy bones")
        proxy_bones.add(item["bone_id"])
        bone = by_id[item["bone_id"]]
        proxy_a = _vector(item.get("a"), "proxy.a")
        proxy_b = _vector(item.get("b"), "proxy.b")
        owned_part = _address_key(item["owned_part"], f"{profile_id} proxy.owned_part")
        if (
            proxy_a != _vector(bone.get("a"), f"{profile_id} proxy bone start")
            or proxy_b != _vector(bone.get("b"), f"{profile_id} proxy bone end")
            or owned_part != _address_key(bone.get("owned_part"), f"{profile_id} proxy bone owner")
        ):
            raise GalleryError(f"{profile_id} proxy endpoints or ownership do not match its bone")
        if item["partition_rule"] != "nearest eligible weighted bone, then ascending derived bone id":
            raise GalleryError(f"{profile_id} proxy partition rule is unsupported")
        if item["radius_rule"] != "maximum point-to-segment distance over the bone's complete primary-influence partition":
            raise GalleryError(f"{profile_id} proxy radius rule is unsupported")
        partition_count = item["partition_vertex_count"]
        if type(partition_count) is not int or partition_count <= 0 or partition_count > len(neutral["vertices"]):
            raise GalleryError(f"{profile_id} proxy partition count is invalid")
        if primary_counts.get(item["bone_id"], 0) != partition_count:
            raise GalleryError(f"{profile_id} proxy partition count does not match primary influences")
        partition_total += partition_count
        radius = item.get("radius")
        if isinstance(radius, bool) or not isinstance(radius, (int, float)) or not math.isfinite(float(radius)) or float(radius) <= EPSILON:
            raise GalleryError(f"{profile_id} proxy radius is invalid")
        primary_vertices = [
            neutral["vertices"][index]
            for index, row in enumerate(rows)
            if min(row, key=lambda influence: (-float(influence["weight"]), influence["bone_id"]))["bone_id"] == item["bone_id"]
        ]
        expected_radius = max(
            bridge._distance_to_segment(tuple(vertex), proxy_a, proxy_b)
            for vertex in primary_vertices
        )
        if not math.isclose(float(radius), expected_radius, rel_tol=1.0e-12, abs_tol=1.0e-12):
            raise GalleryError(f"{profile_id} proxy radius does not match its complete primary-influence partition")
    if proxy_bones != set(by_id) or partition_total != len(neutral["vertices"]):
        raise GalleryError(f"{profile_id} proxies do not exactly partition every vertex across every bone")


def _quat(axis: str, angle_degrees: float) -> tuple[float, float, float, float]:
    radians = math.radians(angle_degrees) * 0.5
    sine, cosine = math.sin(radians), math.cos(radians)
    if axis == "x":
        result = (sine, 0.0, 0.0, cosine)
    elif axis == "z":
        result = (0.0, 0.0, sine, cosine)
    elif axis == "identity":
        result = (0.0, 0.0, 0.0, 1.0)
    else:
        raise GalleryError("pose contains an unsupported rotation axis")
    rounded = tuple(round(value, 15) for value in result)
    length = math.sqrt(sum(value * value for value in rounded))
    return tuple(round(value / length, 15) for value in rounded)


def _load_pose_with_bytes(path: Path) -> tuple[dict[str, Any], bytes]:
    pose, pose_data = _load_json(path, "shared pose JSON")
    root = _obj(pose, "shared pose JSON")
    _require_fields(root, ("convention", "format", "pose_id", "rules", "solver", "version"), "shared pose JSON")
    if root["format"] != POSE_FORMAT or root["version"] != 1 or root["pose_id"] != "shared-structural-pose-v1":
        raise GalleryError("shared pose identity is unsupported")
    convention = _obj(root["convention"], "shared pose convention")
    if convention.get("vectors") != "column" or convention.get("bind_transform") != "bone-local-plus-y-with-deterministic-up-fallback" or convention.get("skin_transform") != "posed-world-times-inverse-neutral-world":
        raise GalleryError("shared pose transform convention is unsupported")
    solver = _obj(root["solver"], "shared pose solver")
    if solver != {"contact": False, "ik": False}:
        raise GalleryError("shared pose must explicitly disable IK and contact")
    rules = root["rules"]
    if not isinstance(rules, list) or len(rules) != 18:
        raise GalleryError("shared pose must contain exactly 18 explicit bone rules")
    selectors: set[tuple[str, str, tuple[str, ...]]] = set()
    normalized_rules: list[dict[str, Any]] = []
    for index, raw in enumerate(rules):
        rule = _obj(raw, f"shared pose.rules[{index}]")
        _require_fields(rule, ("angle_degrees", "axis", "anchors", "kind", "role", "rotation_xyzw"), f"shared pose.rules[{index}]")
        kind = _text(rule["kind"], "pose rule kind")
        role = rule["role"]
        if role is not None:
            role = _text(role, "pose rule role")
        anchors_raw = rule["anchors"]
        if not isinstance(anchors_raw, list) or any(not isinstance(item, str) or not item for item in anchors_raw):
            raise GalleryError("pose rule anchors are invalid")
        selector = (kind, role or "", tuple(anchors_raw))
        if selector in selectors:
            raise GalleryError("shared pose contains duplicate selectors")
        selectors.add(selector)
        axis = _text(rule["axis"], "pose rule axis")
        angle = rule["angle_degrees"]
        if isinstance(angle, bool) or not isinstance(angle, (int, float)) or not math.isfinite(float(angle)):
            raise GalleryError("pose rule angle is invalid")
        expected_recipe = POSE_RECIPE.get(selector)
        if expected_recipe is None or (axis, float(angle)) != expected_recipe:
            raise GalleryError("shared pose selector axis/angle does not match the exact shared recipe")
        q = _vector(rule["rotation_xyzw"], "pose rule quaternion", 4)
        expected = _quat(axis, float(angle))
        if any(abs(a - b) > 2.0e-14 for a, b in zip(q, expected)) or abs(sum(value * value for value in q) - 1.0) > 2.0e-14:
            raise GalleryError("shared pose quaternion is not fixed, normalized, or bound to its angle")
        normalized_rules.append({"kind": kind, "role": role, "anchors": tuple(anchors_raw), "axis": axis, "angle_degrees": float(angle), "rotation_xyzw": q})
    if selectors != set(POSE_RECIPE):
        raise GalleryError("shared pose does not explicitly cover the exact bridge bone inventory")
    return {"source": root, "rules": normalized_rules}, pose_data


def load_pose(path: Path) -> dict[str, Any]:
    pose, _ = _load_pose_with_bytes(path)
    return pose


def _m_identity() -> tuple[float, ...]:
    return (1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0)


def _m_mul(left: tuple[float, ...], right: tuple[float, ...]) -> tuple[float, ...]:
    return tuple(
        math.fsum(left[row * 4 + k] * right[k * 4 + col] for k in range(4))
        for row in range(4) for col in range(4)
    )


def _m_vec(matrix: tuple[float, ...], vector: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    return tuple(math.fsum(matrix[row * 4 + col] * vector[col] for col in range(4)) for row in range(4))  # type: ignore[return-value]


def _m_rigid_inverse(matrix: tuple[float, ...]) -> tuple[float, ...]:
    rotation = tuple(matrix[row * 4 + col] for row in range(3) for col in range(3))
    translation = (matrix[3], matrix[7], matrix[11])
    transposed = tuple(rotation[col * 3 + row] for row in range(3) for col in range(3))
    inverse_translation = tuple(-math.fsum(transposed[row * 3 + col] * translation[col] for col in range(3)) for row in range(3))
    return (
        transposed[0], transposed[1], transposed[2], inverse_translation[0],
        transposed[3], transposed[4], transposed[5], inverse_translation[1],
        transposed[6], transposed[7], transposed[8], inverse_translation[2],
        0.0, 0.0, 0.0, 1.0,
    )


def _rotation_from_quat(quaternion: tuple[float, float, float, float]) -> tuple[float, ...]:
    x, y, z, w = quaternion
    return (
        1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w), 0.0,
        2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w), 0.0,
        2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y), 0.0,
        0.0, 0.0, 0.0, 1.0,
    )


def _bind_world(start: tuple[float, ...], end: tuple[float, ...]) -> tuple[float, ...]:
    direction = _normalize(tuple(end[index] - start[index] for index in range(3)), "bone endpoint direction")
    for preferred in ((0.0, 0.0, 1.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)):
        projected = tuple(preferred[index] - direction[index] * _dot(preferred, direction) for index in range(3))
        if _length(projected) > EPSILON:
            x_axis = _normalize(projected, "deterministic bind up fallback")
            z_axis = _normalize(_cross(x_axis, direction), "deterministic bind third axis")
            return (
                x_axis[0], direction[0], z_axis[0], start[0],
                x_axis[1], direction[1], z_axis[1], start[1],
                x_axis[2], direction[2], z_axis[2], start[2],
                0.0, 0.0, 0.0, 1.0,
            )
    raise GalleryError("could not derive a deterministic bind frame")


def _dot(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    return math.fsum(a * b for a, b in zip(left, right))


def _cross(left: tuple[float, ...], right: tuple[float, ...]) -> tuple[float, float, float]:
    return (left[1] * right[2] - left[2] * right[1], left[2] * right[0] - left[0] * right[2], left[0] * right[1] - left[1] * right[0])


def _length(value: tuple[float, ...]) -> float:
    return math.sqrt(_dot(value, value))


def _normalize(value: tuple[float, ...], where: str) -> tuple[float, ...]:
    length = _length(value)
    if not math.isfinite(length) or length <= EPSILON:
        raise GalleryError(f"{where} is zero-length or non-finite")
    return tuple(item / length for item in value)


def _round_matrix(matrix: tuple[float, ...]) -> list[float]:
    return [round(value, DECIMAL_PLACES) for value in matrix]


def _bone_selector(bone: dict[str, Any]) -> tuple[str, str, tuple[str, ...]]:
    if bone["kind"] == "synthetic-source-part-root":
        return ("synthetic-root", "", ())
    joint = _obj(bone.get("joint"), "bridge bone joint")
    return ("joint", _text(joint.get("role"), "bridge joint role"), tuple(joint.get("anchors", [])))


def _prepare_profile(profile: dict[str, Any], pose: dict[str, Any]) -> dict[str, Any]:
    candidate = profile["candidate"]
    bones = candidate["hierarchy"]["bones"]
    rule_map = {(item["kind"], item["role"] or "", item["anchors"]): item for item in pose["rules"]}
    by_id = {bone["id"]: bone for bone in bones}
    world_bind: dict[str, tuple[float, ...]] = {}
    local_bind: dict[str, tuple[float, ...]] = {}
    posed_world: dict[str, tuple[float, ...]] = {}
    skin: dict[str, tuple[float, ...]] = {}
    pose_rules: dict[str, dict[str, Any]] = {}
    pending = set(by_id)
    while pending:
        progress = False
        for bone_id in sorted(pending):
            bone = by_id[bone_id]
            parent = bone["parent"]
            if parent is not None and parent not in world_bind:
                continue
            start = _vector(bone["a"], f"{profile['id']} bone start")
            end = _vector(bone["b"], f"{profile['id']} bone end")
            bind_world = _bind_world(start, end)
            world_bind[bone_id] = bind_world
            local_bind[bone_id] = bind_world if parent is None else _m_mul(_m_rigid_inverse(world_bind[parent]), bind_world)
            selector = _bone_selector(bone)
            if selector not in rule_map:
                raise GalleryError(f"{profile['id']} bridge bone is not covered by shared pose: {selector}")
            rule = rule_map[selector]
            pose_rules[bone_id] = rule
            local_pose = _rotation_from_quat(rule["rotation_xyzw"])
            posed_world[bone_id] = _m_mul(local_bind[bone_id], local_pose) if parent is None else _m_mul(_m_mul(posed_world[parent], local_bind[bone_id]), local_pose)
            skin[bone_id] = _m_mul(posed_world[bone_id], _m_rigid_inverse(world_bind[bone_id]))
            pending.remove(bone_id)
            progress = True
        if not progress:
            raise GalleryError(f"{profile['id']} hierarchy cannot be ordered for transforms")
    vertices = [tuple(item) for item in profile["neutral"]["vertices"]]
    normals = [tuple(item) for item in profile["neutral"]["normals"]]
    rows = candidate["weights"]["influences"]
    posed_vertices: list[tuple[float, float, float]] = []
    posed_normals: list[tuple[float, float, float]] = []
    dominant: list[tuple[str, float]] = []
    for index, (point, normal, row) in enumerate(zip(vertices, normals, rows)):
        position_components = []
        normal_components = []
        for influence in row:
            bone_id = influence["bone_id"]
            weight = float(influence["weight"])
            transformed = _m_vec(skin[bone_id], (*point, 1.0))
            position_components.append((weight, transformed[:3]))
            unit_normal = _normalize(tuple(float(value) for value in normal), f"{profile['id']} neutral normal[{index}]")
            rotated = _m_vec(skin[bone_id], (*unit_normal, 0.0))
            normal_components.append((weight, rotated[:3]))
        posed_point = tuple(math.fsum(weight * value[axis] for weight, value in position_components) for axis in range(3))
        blended_normal = tuple(math.fsum(weight * value[axis] for weight, value in normal_components) for axis in range(3))
        posed_vertices.append(posed_point)
        posed_normals.append(_normalize(blended_normal, f"{profile['id']} posed normal[{index}]")[:3])
        winner = min(row, key=lambda item: (-float(item["weight"]), item["bone_id"]))
        dominant.append((winner["bone_id"], float(winner["weight"])))
    neutral_proxies = []
    posed_proxies = []
    for proxy in candidate["proxies"]:
        bone_id = proxy["bone_id"]
        start = tuple(_vector(proxy["a"], "proxy start"))
        end = tuple(_vector(proxy["b"], "proxy end"))
        radius = float(proxy["radius"])
        lineage = {
            "owned_part": proxy["owned_part"],
            "partition_rule": proxy["partition_rule"],
            "partition_vertex_count": proxy["partition_vertex_count"],
            "radius_rule": proxy["radius_rule"],
        }
        neutral_proxies.append({"bone_id": bone_id, "a": list(start), "b": list(end), "radius": radius, "kind": "capsule", **lineage})
        posed_proxies.append({"bone_id": bone_id, "a": list(_m_vec(skin[bone_id], (*start, 1.0))[:3]), "b": list(_m_vec(skin[bone_id], (*end, 1.0))[:3]), "radius": radius, "kind": "capsule", **lineage})
    neutral_skeleton = _skeleton_records(bones, world_bind, posed_world, neutral=True)
    posed_skeleton = _skeleton_records(bones, world_bind, posed_world, neutral=False)
    return {
        **profile,
        "posed_vertices": posed_vertices,
        "posed_normals": posed_normals,
        "dominant": dominant,
        "world_bind": world_bind,
        "local_bind": local_bind,
        "posed_world": posed_world,
        "skin": skin,
        "pose_rules": pose_rules,
        "neutral_proxies": neutral_proxies,
        "posed_proxies": posed_proxies,
        "neutral_skeleton": neutral_skeleton,
        "posed_skeleton": posed_skeleton,
    }


def _skeleton_records(bones: list[dict[str, Any]], world_bind: dict[str, tuple[float, ...]], posed_world: dict[str, tuple[float, ...]], *, neutral: bool) -> list[dict[str, Any]]:
    result = []
    for bone in bones:
        bone_id = bone["id"]
        bind = world_bind[bone_id]
        pose_matrix = posed_world[bone_id] if not neutral else bind
        length = math.dist(_vector(bone["a"], "skeleton a"), _vector(bone["b"], "skeleton b"))
        start = _m_vec(pose_matrix, (0.0, 0.0, 0.0, 1.0))[:3]
        end = _m_vec(pose_matrix, (0.0, length, 0.0, 1.0))[:3]
        record = {
            "id": bone_id,
            "kind": bone["kind"],
            "parent": bone["parent"],
            "a": list(start),
            "b": list(end),
            "length": round(length, DECIMAL_PLACES),
        }
        if "joint" in bone:
            record["joint"] = bone["joint"]
        if "source_part" in bone:
            record["source_part"] = bone["source_part"]
        result.append(record)
    return result


def _ply_bytes(vertices: list[tuple[float, float, float]], normals: list[tuple[float, float, float]], faces: list[tuple[int, int, int]]) -> bytes:
    lines = [
        "ply", "format ascii 1.0", f"element vertex {len(vertices)}", "property float x", "property float y", "property float z", "property float nx", "property float ny", "property float nz", f"element face {len(faces)}", "property list uchar int vertex_indices", "end_header",
    ]
    for point, normal in zip(vertices, normals):
        lines.append(" ".join(f"{value:.12f}" for value in (*point, *normal)))
    lines.extend(f"3 {a} {b} {c}" for a, b, c in faces)
    return ("\n".join(lines) + "\n").encode("ascii")


def _bounds(points: Iterable[tuple[float, float, float]]) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    items = list(points)
    if not items:
        raise GalleryError("cannot derive a bound from no points")
    lower = tuple(min(point[axis] for point in items) for axis in range(3))
    upper = tuple(max(point[axis] for point in items) for axis in range(3))
    if any(not math.isfinite(value) for value in (*lower, *upper)) or any(upper[axis] - lower[axis] <= EPSILON for axis in range(3)):
        raise GalleryError("gallery world bound is degenerate or non-finite")
    return lower, upper


def _all_bound_points(profiles: list[dict[str, Any]]) -> list[tuple[float, float, float]]:
    points: list[tuple[float, float, float]] = []
    for profile in profiles:
        points.extend(profile["neutral"]["vertices"])
        points.extend(profile["posed_vertices"])
        for records in (profile["neutral_skeleton"], profile["posed_skeleton"], profile["neutral_proxies"], profile["posed_proxies"]):
            for item in records:
                radius = float(item.get("radius", 0.0))
                for endpoint in (item["a"], item["b"]):
                    point = tuple(float(value) for value in endpoint)
                    points.append(point)
                    if radius:
                        for axis in range(3):
                            plus = list(point)
                            minus = list(point)
                            plus[axis] += radius
                            minus[axis] -= radius
                            points.extend((tuple(plus), tuple(minus)))
    return points


def _projection_horizontal_bounds(view: str, lower: tuple[float, ...], upper: tuple[float, ...]) -> tuple[float, float]:
    if view == "front":
        return lower[0], upper[0]
    if view == "side":
        return lower[2], upper[2]
    if view == "three-quarter":
        return (
            (lower[0] - upper[2] * THREE_QUARTER_DEPTH_FACTOR) / THREE_QUARTER_BASIS_NORM,
            (upper[0] - lower[2] * THREE_QUARTER_DEPTH_FACTOR) / THREE_QUARTER_BASIS_NORM,
        )
    raise GalleryError(f"unsupported gallery view: {view}")


def _pixels_per_world_unit(lower: tuple[float, ...], upper: tuple[float, ...], box: tuple[int, int, int, int]) -> float:
    horizontal_spans = tuple(
        upper_bound - lower_bound
        for lower_bound, upper_bound in (
            _projection_horizontal_bounds(view, lower, upper)
            for view in ("front", "side", "three-quarter")
        )
    )
    vertical_span = upper[1] - lower[1]
    return min(box[2] / max(horizontal_spans), box[3] / vertical_span)


def _project(point: tuple[float, float, float], view: str, lower: tuple[float, ...], upper: tuple[float, ...], box: tuple[int, int, int, int]) -> tuple[float, float]:
    left, top, width, height = box
    pixels_per_unit = _pixels_per_world_unit(lower, upper, box)
    horizontal_lower, horizontal_upper = _projection_horizontal_bounds(view, lower, upper)
    horizontal_center = (horizontal_lower + horizontal_upper) * 0.5
    vertical_center = (lower[1] + upper[1]) * 0.5
    if view == "front":
        horizontal, vertical = point[0], point[1]
    elif view == "side":
        horizontal, vertical = point[2], point[1]
    else:
        horizontal = (point[0] - point[2] * THREE_QUARTER_DEPTH_FACTOR) / THREE_QUARTER_BASIS_NORM
        vertical = point[1]
    x = left + width * 0.5 + (horizontal - horizontal_center) * pixels_per_unit
    y = top + height * 0.5 - (vertical - vertical_center) * pixels_per_unit
    return x, y


def _hue(bone_id: str, brightness: float) -> tuple[int, int, int]:
    digest = hashlib.sha256(bone_id.encode("utf-8")).digest()
    hue = (digest[0] / 255.0) * 360.0
    saturation, value = 0.78, max(0.28, min(1.0, brightness))
    c = value * saturation
    x = c * (1 - abs((hue / 60.0) % 2 - 1))
    m = value - c
    if hue < 60:
        rgb = (c, x, 0)
    elif hue < 120:
        rgb = (x, c, 0)
    elif hue < 180:
        rgb = (0, c, x)
    elif hue < 240:
        rgb = (0, x, c)
    elif hue < 300:
        rgb = (x, 0, c)
    else:
        rgb = (c, 0, x)
    return tuple(int(round((value + m) * 255)) for value in rgb)


def _bone_color(bone_id: str, brightness: float = 0.86) -> tuple[int, int, int]:
    """Return the stable palette color shared by all bone-bound overlays."""
    return _hue(bone_id, brightness)


def _dominant_vertex_color(dominant: tuple[str, float]) -> tuple[int, int, int]:
    """Encode dominant-bone hue and max-weight brightness for one vertex."""
    bone_id, max_weight = dominant
    brightness = 0.30 + 0.70 * max(0.0, min(1.0, float(max_weight)))
    return _bone_color(bone_id, brightness)


def _face_depth(point: tuple[float, float, float], view: str) -> float:
    if view == "front":
        return point[2]
    if view == "side":
        return point[0]
    if view == "three-quarter":
        return (point[0] * THREE_QUARTER_DEPTH_FACTOR + point[2]) / THREE_QUARTER_BASIS_NORM
    raise GalleryError(f"unsupported gallery view: {view}")


def _ordered_face_indices(vertices: list[tuple[float, float, float]], faces: list[tuple[int, int, int]], view: str) -> list[int]:
    if len(faces) > MAX_RENDER_FACES:
        stride = math.ceil(len(faces) / MAX_RENDER_FACES)
    else:
        stride = 1
    sampled = range(0, len(faces), stride)
    return sorted(
        sampled,
        key=lambda face_index: (
            math.fsum(_face_depth(vertices[vertex_index], view) for vertex_index in faces[face_index]) / 3.0,
            face_index,
        ),
    )


def _draw_surface(draw: ImageDraw.ImageDraw, vertices: list[tuple[float, float, float]], faces: list[tuple[int, int, int]], view: str, lower: tuple[float, ...], upper: tuple[float, ...], box: tuple[int, int, int, int], color_for_face: Any) -> None:
    for face_index in _ordered_face_indices(vertices, faces, view):
        face = faces[face_index]
        polygon = [_project(vertices[index], view, lower, upper, box) for index in face]
        draw.polygon(polygon, fill=color_for_face(face), outline=(34, 38, 48))


def _draw_skeleton(draw: ImageDraw.ImageDraw, records: list[dict[str, Any]], view: str, lower: tuple[float, ...], upper: tuple[float, ...], box: tuple[int, int, int, int], *, palette: bool = False) -> None:
    for item in records:
        start = _project(tuple(item["a"]), view, lower, upper, box)
        end = _project(tuple(item["b"]), view, lower, upper, box)
        color = _bone_color(item["id"]) if palette else (246, 244, 230)
        draw.line((start, end), fill=color, width=3)
        draw.ellipse((start[0] - 3, start[1] - 3, start[0] + 3, start[1] + 3), fill=color)


def _draw_influence_vertices(
    draw: ImageDraw.ImageDraw,
    vertices: list[tuple[float, float, float]],
    dominant: list[tuple[str, float]],
    view: str,
    lower: tuple[float, ...],
    upper: tuple[float, ...],
    box: tuple[int, int, int, int],
) -> None:
    """Draw one exact dominant-bone/max-weight marker for every surface vertex."""
    if len(vertices) != len(dominant):
        raise GalleryError("influence marker data does not match neutral vertex count")
    for vertex, influence in zip(vertices, dominant):
        x, y = _project(vertex, view, lower, upper, box)
        radius = 3
        color = _dominant_vertex_color(influence)
        draw.ellipse((round(x) - radius, round(y) - radius, round(x) + radius, round(y) + radius), fill=color, outline=(12, 15, 21), width=1)


def _projected_capsule_side_boundaries(
    start: tuple[float, float], end: tuple[float, float], radius: float
) -> tuple[tuple[tuple[float, float], tuple[float, float]], ...]:
    """Return the two parallel projected side boundaries of a capsule."""
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.hypot(dx, dy)
    if length <= EPSILON:
        return ()
    normal = (-dy / length * radius, dx / length * radius)
    return (
        (
            (start[0] + normal[0], start[1] + normal[1]),
            (end[0] + normal[0], end[1] + normal[1]),
        ),
        (
            (start[0] - normal[0], start[1] - normal[1]),
            (end[0] - normal[0], end[1] - normal[1]),
        ),
    )


def _projected_capsule_outline(
    start: tuple[float, float], end: tuple[float, float], radius: float, *, arc_steps: int = CAPSULE_ARC_STEPS
) -> tuple[tuple[float, float], ...]:
    """Return the orthographic projected outer boundary of a capsule.

    A 3D capsule projects to the Minkowski sum of the projected segment and a
    disk.  The result is therefore one stadium outline, or one circle when
    the projected segment collapses (including endpoints separated only in
    the view-depth axis).
    """
    if arc_steps < 2:
        raise GalleryError("capsule outline requires at least two arc steps")
    radius = float(radius)
    if not math.isfinite(radius) or radius <= 0.0:
        raise GalleryError("capsule outline radius must be positive and finite")
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.hypot(dx, dy)
    if length <= EPSILON:
        return tuple(
            (
                start[0] + radius * math.cos(math.tau * index / arc_steps),
                start[1] + radius * math.sin(math.tau * index / arc_steps),
            )
            for index in range(arc_steps)
        )

    normal = (-dy / length * radius, dx / length * radius)
    normal_angle = math.atan2(normal[1], normal[0])
    outline: list[tuple[float, float]] = []
    for index in range(arc_steps + 1):
        angle = normal_angle - math.pi * index / arc_steps
        outline.append((end[0] + radius * math.cos(angle), end[1] + radius * math.sin(angle)))
    for index in range(arc_steps + 1):
        angle = normal_angle + math.pi - math.pi * index / arc_steps
        outline.append((start[0] + radius * math.cos(angle), start[1] + radius * math.sin(angle)))
    return tuple(outline)


def _proxy_radius_pixels(radius: float, lower: tuple[float, ...], upper: tuple[float, ...], box: tuple[int, int, int, int]) -> float:
    return float(radius) * _pixels_per_world_unit(lower, upper, box)


def _proxy_draw_colors(draw: ImageDraw.ImageDraw, bone_id: str) -> tuple[tuple[int, ...], tuple[int, ...]]:
    color = _bone_color(bone_id)
    image = getattr(draw, "_image", None)
    if image is not None and image.mode == "RGBA":
        return (*color, 54), (*color, 224)
    # Direct RGB callers (including small focused tests) get the same visual
    # discipline without pretending that ImageDraw can alpha-composite RGB.
    blended = tuple(round(0.76 * base + 0.24 * component) for base, component in zip((20, 23, 29), color))
    return blended, color


def _draw_proxies(draw: ImageDraw.ImageDraw, records: list[dict[str, Any]], view: str, lower: tuple[float, ...], upper: tuple[float, ...], box: tuple[int, int, int, int]) -> None:
    canvas = getattr(draw, "_image", None)
    for item in records:
        start = _project(tuple(item["a"]), view, lower, upper, box)
        end = _project(tuple(item["b"]), view, lower, upper, box)
        radius_pixels = _proxy_radius_pixels(float(item["radius"]), lower, upper, box)
        outline = _projected_capsule_outline(start, end, radius_pixels)
        fill, edge = _proxy_draw_colors(draw, item.get("bone_id", "proxy"))
        if canvas is not None and canvas.mode == "RGBA":
            layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
            layer_draw = ImageDraw.Draw(layer)
            layer_draw.polygon(outline, fill=fill)
            layer_draw.line((*outline, outline[0]), fill=edge, width=2, joint="curve")
            canvas.alpha_composite(layer)
        else:
            draw.polygon(outline, fill=fill)
            draw.line((*outline, outline[0]), fill=edge, width=2, joint="curve")


def _draw_palette_legend(draw: ImageDraw.ImageDraw, records: list[dict[str, Any]], box: tuple[int, int, int, int]) -> None:
    """Draw a compact, deterministic mapping from readable selectors to hues."""
    columns = 3
    rows = math.ceil(len(records) / columns)
    swatch = 8
    row_height = 12
    padding = 6
    legend_width = box[2] - 16
    legend_height = rows * row_height + padding * 2
    left = box[0] + 8
    top = box[1] + box[3] - legend_height - 8
    draw.rectangle((left, top, left + legend_width, top + legend_height), fill=(20, 23, 29), outline=(85, 92, 106), width=1)
    column_width = legend_width // columns
    for index, item in enumerate(records):
        column = index // rows
        row = index % rows
        x = left + padding + column * column_width
        y = top + padding + row * row_height
        draw.rectangle((x, y + 1, x + swatch, y + 1 + swatch), fill=_bone_color(item["id"]), outline=(8, 10, 14), width=1)
        draw.text((x + swatch + 4, y), _bone_label(item), fill=(214, 218, 228))


def _bone_label(bone: dict[str, Any]) -> str:
    kind, role, anchors = _bone_selector(bone)
    return "root" if kind == "synthetic-root" else " ".join((*anchors, role.replace("_", " ")))


def _gallery_row_header(profile: dict[str, Any], row: int, row_name: str) -> str:
    if row == 0:
        return f"PROFILE: {profile['id']} | {profile['label']} | {row_name}"
    return row_name


def _render_gallery(profile: dict[str, Any], bound: tuple[tuple[float, ...], tuple[float, ...]]) -> bytes:
    lower, upper = bound
    image = Image.new("RGB", CANVAS, (20, 23, 29))
    draw = ImageDraw.Draw(image)
    row_names = ("NEUTRAL SKIN + SKELETON", "POSED SKIN + SKELETON", "PER-VERTEX DOMINANT BONE / MAX WEIGHT", "NEUTRAL SKIN + PROXIES", "POSED SKIN + PROXIES")
    views = ("front", "side", "three-quarter")
    for row, name in enumerate(row_names):
        y = row * PANEL_HEIGHT
        draw.rectangle((0, y, CANVAS[0] - 1, y + PANEL_HEIGHT - 1), outline=(61, 67, 80), width=1)
        draw.text((8, y + 8), _gallery_row_header(profile, row, name), fill=(224, 226, 232))
        proxy_layer = Image.new("RGBA", CANVAS, (0, 0, 0, 0)) if row in (3, 4) else None
        proxy_draw = ImageDraw.Draw(proxy_layer) if proxy_layer is not None else None
        for column, view in enumerate(views):
            x = column * PANEL_WIDTH
            box = (x + 12, y + 34, PANEL_WIDTH - 24, PANEL_HEIGHT - 46)
            draw.text((x + 12, y + 17), view, fill=(151, 158, 174))
            draw.rectangle((box[0], box[1], box[0] + box[2], box[1] + box[3]), outline=(45, 51, 63), width=1)
            vertices = profile["neutral"]["vertices"] if row in (0, 2, 3) else profile["posed_vertices"]
            faces = profile["neutral"]["faces"]
            if row == 2:
                color_for_face = lambda face: (55, 63, 76)
            else:
                color_for_face = lambda face: (84, 121, 166) if row in (0, 1) else (80, 116, 148)
            _draw_surface(draw, vertices, faces, view, lower, upper, box, color_for_face)
            if row == 0:
                _draw_skeleton(draw, profile["neutral_skeleton"], view, lower, upper, box)
            elif row == 1:
                _draw_skeleton(draw, profile["posed_skeleton"], view, lower, upper, box)
            elif row == 2:
                _draw_skeleton(draw, profile["neutral_skeleton"], view, lower, upper, box, palette=True)
                _draw_influence_vertices(draw, vertices, profile["dominant"], view, lower, upper, box)
                if column == 0:
                    _draw_palette_legend(draw, profile["neutral_skeleton"], box)
            elif row == 3:
                assert proxy_draw is not None
                _draw_proxies(proxy_draw, profile["neutral_proxies"], view, lower, upper, box)
            elif row == 4:
                assert proxy_draw is not None
                _draw_proxies(proxy_draw, profile["posed_proxies"], view, lower, upper, box)
        if proxy_layer is not None:
            image = Image.alpha_composite(image.convert("RGBA"), proxy_layer).convert("RGB")
            draw = ImageDraw.Draw(image)
    output = tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode="w+b")
    image.save(output, format="PNG", optimize=False, compress_level=9)
    output.seek(0)
    data = output.read()
    output.close()
    if len(data) > MAX_ARTIFACT_BYTES:
        raise GalleryError("rendered gallery exceeds the bounded artifact size")
    return data


def _no_temp_provenance(value: Any) -> None:
    if isinstance(value, str):
        lowered = value.lower().replace("\\", "/")
        if lowered.startswith("/") or "/tmp/" in lowered or "/temp/" in lowered or "\\temp\\" in lowered:
            raise GalleryError("published evidence contains temporary or absolute path provenance")
    elif isinstance(value, list):
        for item in value:
            _no_temp_provenance(item)
    elif isinstance(value, dict):
        for item in value.values():
            _no_temp_provenance(item)


def _write_artifact(stage: Path, relative: str, data: bytes) -> dict[str, Any]:
    _safe_relative(relative, "output artifact path")
    if len(data) > MAX_ARTIFACT_BYTES:
        raise GalleryError(f"output artifact {relative} exceeds the bounded size")
    path = stage / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {"path": relative, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


def _atomic_publish_no_replace(parent_fd: int, stage_name: str, destination_name: str) -> None:
    try:
        structural_atomic_publish.publish_no_replace(parent_fd, stage_name, destination_name)
    except FileExistsError as exc:
        raise GalleryError("refusing to overwrite existing gallery output") from exc
    except structural_atomic_publish.AtomicPublishError as exc:
        raise GalleryError(str(exc)) from exc


def build(
    inputs: Mapping[str, ProfileInput | tuple[Path, Path, Path]],
    output: Path,
    *,
    source_manifest_path: Path,
    candidate_path: Path | None = None,
    pose_path: Path | None = None,
) -> dict[str, Any]:
    """Consume exactly four profile inputs and atomically publish the gallery."""
    if set(inputs) != set(FROZEN_PROFILE_IDS) or len(inputs) != MAX_PROFILES:
        raise GalleryError("gallery requires exactly the four frozen candidate profile IDs")
    normalized: dict[str, ProfileInput] = {}
    for profile_id in FROZEN_PROFILE_IDS:
        record = inputs[profile_id]
        if isinstance(record, ProfileInput):
            if record.inspect_structure is None:
                raise GalleryError(f"{profile_id} requires its own inspect-structure JSON")
            normalized[profile_id] = record
        elif isinstance(record, tuple) and len(record) == 3:
            normalized[profile_id] = ProfileInput(Path(record[0]), Path(record[1]), Path(record[2]))
        else:
            raise GalleryError(f"{profile_id} input record must include bridge, neutral PLY, and inspect-structure paths")
    candidate_table = _load_candidates(candidate_path or Path(__file__).with_name(CANDIDATE_FILE))
    source_set = _load_source_manifest(source_manifest_path, candidate_table)
    pose_file = pose_path or Path(__file__).with_name(POSE_FILE)
    pose, pose_file_bytes = _load_pose_with_bytes(pose_file)
    loaded = [
        _validate_bridge(profile_id, normalized[profile_id], candidate_table, source_set["profiles"][profile_id])
        for profile_id in FROZEN_PROFILE_IDS
    ]
    prepared = [_prepare_profile(profile, pose) for profile in loaded]
    lower, upper = _bounds(_all_bound_points(prepared))
    bound = {"min": list(lower), "max": list(upper)}
    profile_records: list[dict[str, Any]] = []
    output_artifacts: list[dict[str, Any]] = []
    _reject_symlink_components(output, "gallery output path")
    parent_identity = _directory_identity(output.parent, "gallery output parent")
    parent_fd: int | None = None
    stage_name: str | None = None
    try:
        parent_fd = structural_atomic_publish.open_directory_no_symlinks(output.parent)
        parent_info = os.fstat(parent_fd)
        if not stat.S_ISDIR(parent_info.st_mode) or (parent_info.st_dev, parent_info.st_ino) != parent_identity:
            raise GalleryError("gallery output parent changed between validation and open")
        try:
            os.stat(output.name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise GalleryError("refusing to overwrite existing gallery output")
        stage_name, stage = structural_atomic_publish.create_stage(parent_fd, output.name)
    except GalleryError:
        if parent_fd is not None:
            os.close(parent_fd)
        raise
    except (OSError, structural_atomic_publish.AtomicPublishError) as exc:
        if parent_fd is not None:
            os.close(parent_fd)
        raise GalleryError(f"could not create secure gallery staging: {exc}") from exc
    try:
        total_output_bytes = 0

        def add_artifact(relative: str, data: bytes) -> dict[str, Any]:
            nonlocal total_output_bytes
            if len(output_artifacts) >= MAX_OUTPUT_ARTIFACTS:
                raise GalleryError("gallery output exceeds the bounded artifact count")
            entry = _write_artifact(stage, relative, data)
            total_output_bytes += entry["bytes"]
            if total_output_bytes > MAX_TOTAL_OUTPUT_BYTES:
                raise GalleryError("gallery output exceeds the bounded total size")
            output_artifacts.append(entry)
            return entry

        add_artifact(CANDIDATE_FILE, candidate_table["data"])
        add_artifact(f"{SOURCES_DIR}/{SOURCE_MANIFEST_FILE}", source_set["manifest_data"])
        for profile_id in FROZEN_PROFILE_IDS:
            add_artifact(f"{SOURCES_DIR}/{profile_id}.json", source_set["profiles"][profile_id]["data"])

        for profile in prepared:
            profile_id = profile["id"]
            prefix = profile_id
            gallery_path = f"{prefix}/{GALLERY_FILE}"
            gallery_bytes = _render_gallery(profile, (lower, upper))
            neutral_data = profile["neutral_data"]
            posed_data = _ply_bytes(profile["posed_vertices"], profile["posed_normals"], profile["neutral"]["faces"])
            skeleton_data = _output_json({
                "format": GALLERY_FORMAT,
                "profile_id": profile_id,
                "convention": {"vectors": "column", "matrices": "row-major storage with column-vector multiplication"},
                "neutral": {"bones": profile["neutral_skeleton"], "bind_world": {key: _round_matrix(value) for key, value in sorted(profile["world_bind"].items())}, "bind_parent_local": {key: _round_matrix(value) for key, value in sorted(profile["local_bind"].items())}},
                "posed": {"bones": profile["posed_skeleton"], "posed_world": {key: _round_matrix(value) for key, value in sorted(profile["posed_world"].items())}, "skin": {key: _round_matrix(value) for key, value in sorted(profile["skin"].items())}},
            })
            weights_data = _output_json({"format": GALLERY_FORMAT, "profile_id": profile_id, "vertex_count": len(profile["neutral"]["vertices"]), "influences": profile["candidate"]["weights"]["influences"], "dominant": [{"bone_id": bone_id, "max_weight": weight} for bone_id, weight in profile["dominant"]]})
            neutral_proxy_data = _output_json({"format": GALLERY_FORMAT, "profile_id": profile_id, "state": "neutral", "radius_transform": "unchanged", "proxies": profile["neutral_proxies"]})
            posed_proxy_data = _output_json({"format": GALLERY_FORMAT, "profile_id": profile_id, "state": "posed", "radius_transform": "unchanged", "proxies": profile["posed_proxies"]})
            profile_metrics = {
                "format": GALLERY_FORMAT,
                "profile_id": profile_id,
                "neutral_vertex_count": len(profile["neutral"]["vertices"]),
                "posed_vertex_count": len(profile["posed_vertices"]),
                "face_count": len(profile["neutral"]["faces"]),
                "bone_count": len(profile["neutral_skeleton"]),
                "proxy_count": len(profile["neutral_proxies"]),
                "neutral_bounds": {"min": list(_bounds(profile["neutral"]["vertices"])[0]), "max": list(_bounds(profile["neutral"]["vertices"])[1])},
                "posed_bounds": {"min": list(_bounds(profile["posed_vertices"])[0]), "max": list(_bounds(profile["posed_vertices"])[1])},
                "pose_rule_count": len(profile["pose_rules"]),
                "source_joint_frame_policy": "identity-only-validated-from-hash-bound-structure",
                "gallery_global_world_bound": bound,
            }
            metrics_data = _output_json(profile_metrics)
            artifacts = []
            for name, data in ((NEUTRAL_FILE, neutral_data), (POSED_FILE, posed_data), (SKELETON_FILE, skeleton_data), (WEIGHTS_FILE, weights_data), (NEUTRAL_PROXIES_FILE, neutral_proxy_data), (POSED_PROXIES_FILE, posed_proxy_data), (METRICS_FILE, metrics_data)):
                artifacts.append(add_artifact(f"{prefix}/{name}", data))
            artifacts.append(add_artifact(gallery_path, gallery_bytes))
            profile_record = {
                "id": profile_id,
                "label": profile["label"],
                "bridge_manifest_sha256": profile["manifest_hash"],
                "bridge_json_sha256": profile["bridge_hash"],
                "neutral_source_sha256": profile["neutral_hash"],
                "neutral_source_bytes": profile["neutral_bytes"],
                "structure_source_sha256": profile["structure_hash"],
                "structure_source_bytes": profile["structure_bytes"],
                "generated_source_path": profile["generated_source_path"],
                "generated_source_sha256": profile["generated_source_sha256"],
                "generated_source_bytes": profile["generated_source_bytes"],
                "candidate_profile_sha256": profile["candidate_profile_sha256"],
                "source": {
                    "document": profile["candidate"]["source"]["document"],
                    "namespace": profile["candidate"]["source"]["namespace"],
                    "candidate_sha256": profile["manifest"]["candidate_sha256"],
                    "request_sha256": profile["manifest"]["request_sha256"],
                },
                "gallery": {"path": gallery_path, "global_world_bound": bound},
                "artifacts": artifacts,
                "metrics": profile_metrics,
            }
            profile_records.append(profile_record)
        add_artifact(POSE_FILE, pose_file_bytes)
        root_manifest = {
            "format": MANIFEST_FORMAT,
            "status": "success",
            "gallery_format": GALLERY_FORMAT,
            "pose_format": POSE_FORMAT,
            "pose_sha256": hashlib.sha256(pose_file_bytes).hexdigest(),
            "pose_id": pose["source"]["pose_id"],
            "candidate_table": {
                "kind": "candidate-table",
                "path": CANDIDATE_FILE,
                "sha256": candidate_table["sha256"],
                "bytes": candidate_table["bytes"],
                "profile_sha256": {profile_id: _candidate_profile_identity(candidate_table, profile_id) for profile_id in FROZEN_PROFILE_IDS},
            },
            "source_manifest": {
                "kind": "generated-source-manifest",
                "path": f"{SOURCES_DIR}/{SOURCE_MANIFEST_FILE}",
                "sha256": source_set["manifest_sha256"],
                "bytes": source_set["manifest_bytes"],
                "base_source_sha256": source_set["manifest"]["source"]["source_sha256"],
            },
            "profile_ids": list(FROZEN_PROFILE_IDS),
            "profiles": profile_records,
            "global_world_bound": bound,
            "canvas": {"width": CANVAS[0], "height": CANVAS[1], "mode": "RGB", "columns": ["front", "side", "three-quarter"], "rows": ["neutral skin+skeleton", "posed skin+skeleton", "per-vertex dominant-bone hue/max-weight brightness", "neutral skin+proxies", "posed skin+proxies"]},
            "transform_convention": {"vectors": "column", "bind": "bone +Y follows endpoints; deterministic up fallback +Z then +X then +Y", "parent_local_bind": "inverse(parent_world_bind) * child_world_bind", "posed_world": "parent_posed_world * parent_local_bind * local_pose_rotation", "skin": "posed_world * inverse(neutral_world_bind)", "skinning": "classic linear blend positions and weighted rotated normalized normals", "proxy_radius": "unchanged"},
            "boundary": "candidate-scoped disposable structural evidence; no muscles, anatomy, IK, contacts, runtime, engine, or VR",
            "lineage": {
                "source": "frozen candidate table, generated source manifest/documents, hash-bound bridge manifests, bridge JSON, neutral PLYs, and per-profile identity-frame structures",
                "build": "shared deterministic structural embodiment gallery v1",
                "scenario": {"id": "shared-structural-pose-v1", "surface_variant_id": NEUTRAL_VARIANT_ID, "pose_id": pose["source"]["pose_id"]},
            },
            "artifacts": sorted(output_artifacts, key=lambda item: item["path"]),
        }
        _no_temp_provenance(root_manifest)
        manifest_data = _output_json(root_manifest)
        output_artifacts.append(_write_artifact(stage, MANIFEST_FILE, manifest_data))
        expected_files = {item["path"] for item in output_artifacts}
        actual_files, actual_dirs = _scan_tree(stage)
        expected_dirs = {profile_id for profile_id in FROZEN_PROFILE_IDS} | {SOURCES_DIR}
        if actual_files != expected_files or actual_dirs != expected_dirs:
            raise GalleryError("staging gallery does not match its explicit inventory")
        _atomic_publish_no_replace(parent_fd, stage_name, output.name)
        return {"manifest": root_manifest, "global_world_bound": bound}
    except Exception:
        structural_atomic_publish.cleanup_stage(parent_fd, stage_name)
        raise
    finally:
        os.close(parent_fd)


def _parse_assignment(value: str) -> tuple[str, Path, Path, Path]:
    pieces = value.split("=", 1)
    if len(pieces) != 2:
        raise GalleryError("--profile must be ID=BRIDGE_DIR,NEUTRAL_PLY,STRUCTURE_JSON")
    profile_id, paths = pieces
    triple = paths.split(",")
    if len(triple) != 3 or not profile_id or any(not item for item in triple):
        raise GalleryError("--profile must be ID=BRIDGE_DIR,NEUTRAL_PLY,STRUCTURE_JSON")
    return profile_id, Path(triple[0]), Path(triple[1]), Path(triple[2])


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the four-profile shared-pose structural embodiment gallery")
    parser.add_argument("--profile", action="append", help="repeat exactly four times as ID=BRIDGE_DIR,NEUTRAL_PLY,STRUCTURE_JSON")
    parser.add_argument("--bridge-root", type=Path, help="root containing exactly one bridge directory per frozen profile ID")
    parser.add_argument("--neutral-ply-root", type=Path, help="root containing exactly one neutral-v0/surface.ply per frozen profile ID")
    parser.add_argument("--structure-root", type=Path, help="root containing exactly one <profile-id>.json hash-bound structure file per frozen profile ID")
    parser.add_argument("--source-manifest", type=Path, required=True, help="generated four-profile source manifest.json")
    parser.add_argument("--candidate-table", type=Path, default=Path(__file__).with_name("structural_profile_candidates.json"))
    parser.add_argument("--pose", type=Path, default=Path(__file__).with_name(POSE_FILE))
    parser.add_argument("--output", type=Path, required=True)
    return parser


def _inputs_from_args(args: argparse.Namespace) -> dict[str, ProfileInput]:
    if args.profile and (args.bridge_root or args.neutral_ply_root or args.structure_root):
        raise GalleryError("use either --profile assignments or the three parallel input roots")
    if args.profile:
        if len(args.profile) != MAX_PROFILES:
            raise GalleryError("--profile must be supplied exactly four times")
        result: dict[str, ProfileInput] = {}
        for raw in args.profile:
            profile_id, bridge_dir, neutral_ply, structure = _parse_assignment(raw)
            if profile_id in result:
                raise GalleryError("--profile contains duplicate candidate IDs")
            result[profile_id] = ProfileInput(bridge_dir, neutral_ply, structure)
        return result
    if args.bridge_root is None or args.neutral_ply_root is None or args.structure_root is None:
        raise GalleryError("provide either four --profile assignments or all three parallel input roots")
    _directory(args.bridge_root, "bridge root")
    _directory(args.neutral_ply_root, "neutral PLY root")
    _directory(args.structure_root, "structure root")
    bridge_entries = {entry.name for entry in os.scandir(args.bridge_root)}
    ply_entries = {entry.name for entry in os.scandir(args.neutral_ply_root)}
    structure_entries = {entry.name for entry in os.scandir(args.structure_root)}
    expected_entries = set(FROZEN_PROFILE_IDS)
    if bridge_entries != expected_entries or ply_entries != expected_entries or structure_entries != {f"{profile_id}.json" for profile_id in FROZEN_PROFILE_IDS}:
        raise GalleryError("parallel input roots must contain exactly the four frozen candidate IDs and structure files")
    result = {}
    for profile_id in FROZEN_PROFILE_IDS:
        bridge_dir = args.bridge_root / profile_id
        candidates = [args.neutral_ply_root / profile_id / "surface.ply", args.neutral_ply_root / profile_id / "neutral.ply", args.neutral_ply_root / profile_id / NEUTRAL_VARIANT_ID / "surface.ply"]
        existing = [path for path in candidates if path.exists()]
        if len(existing) != 1:
            raise GalleryError(f"{profile_id} must have exactly one supported neutral PLY path")
        result[profile_id] = ProfileInput(bridge_dir, existing[0], args.structure_root / f"{profile_id}.json")
    return result


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        result = build(
            _inputs_from_args(args),
            args.output,
            source_manifest_path=args.source_manifest,
            candidate_path=args.candidate_table,
            pose_path=args.pose,
        )
    except (GalleryError, OSError, ValueError) as exc:
        message = str(exc).replace("\n", " ")[:240] or "gallery failed"
        print(json.dumps({"format": GALLERY_FORMAT, "status": "failure", "error": message}, sort_keys=True, separators=(",", ":")), file=sys.stderr)
        return 2
    print(json.dumps({"format": GALLERY_FORMAT, "status": "success", "output": str(args.output), "global_world_bound": result["global_world_bound"]}, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

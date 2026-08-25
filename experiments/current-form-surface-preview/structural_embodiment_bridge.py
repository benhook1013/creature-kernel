#!/usr/bin/env python3
"""Candidate-scoped structural embodiment bridge.

This module deliberately consumes only inspection JSON and an immutable surface
bundle.  It does not import the surface generators, does not select a rig or
runtime format, and does not emit pose data.  The JSON written here is
disposable experiment evidence rather than a public or production contract.
"""

from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import json
import math
import os
import re
import shutil
import stat
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any


BRIDGE_FORMAT = "creature-kernel.disposable-structural-embodiment-bridge.v1"
MANIFEST_FORMAT = "creature-kernel.disposable-structural-embodiment-bridge-manifest.v1"
SOURCE_FORMAT = "creature-kernel.provisional-form-preview.v11"
STRUCTURE_FORMAT = "creature-kernel.provisional-structural-inspection.v1"
SUCCESSOR_FORMAT = "creature-kernel.disposable-successor-surface-preview.v9"
SEMANTIC_FORMAT = "creature-kernel.disposable-surface-preview-semantic-winners.v1"
ALGORITHM_REVISION = "structural-embodiment-bridge-algorithm-v2"
CONFIGURATION_REVISION = "owner-adjacency-inverse-distance-primary-partition-capsule-v2"
BRIDGE_FILE = "structural-embodiment-bridge.json"
MANIFEST_FILE = "structural-embodiment-bridge-manifest.json"
MAX_JSON_BYTES = 16 * 1024 * 1024
MAX_JSON_NODES = 800_000
MAX_JSON_DEPTH = 96
MAX_STRING_LENGTH = 65_536
MAX_PARTS = 512
MAX_JOINTS = 512
MAX_VARIANTS = 8
MAX_DESCRIPTORS = 512
MAX_PLY_BYTES = 16 * 1024 * 1024
MAX_PLY_VERTICES = 100_000
MAX_PLY_FACES = 200_000
MAX_OUTPUT_VERTICES = 100_000
MAX_BUNDLE_ENTRIES = 512
MAX_BUNDLE_DEPTH = 4
MAX_INFLUENCES = 4
MIN_SEGMENT_LENGTH = 1.0e-12
MIN_RADIUS = 1.0e-12
IDENTITY_DOMAIN = "creature-kernel.structural-embodiment-bridge.identity"
CANDIDATE_PROFILE_ID = re.compile(r"^[a-z][a-z0-9_]*$")


class BridgeError(ValueError):
    """A bounded, user-actionable bridge validation or publication failure."""


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
        raise BridgeError("value cannot be encoded as canonical finite JSON") from exc


def _digest(domain: str, value: Any) -> str:
    return hashlib.sha256(
        (domain + "\0").encode("utf-8") + _canonical(value)
    ).hexdigest()


def _finite_json(value: Any, where: str = "json", *, depth: int = 0, state: list[int] | None = None) -> None:
    if state is None:
        state = [0]
    state[0] += 1
    if state[0] > MAX_JSON_NODES:
        raise BridgeError(f"{where} exceeds the bounded JSON node count")
    if depth > MAX_JSON_DEPTH:
        raise BridgeError(f"{where} exceeds the bounded JSON depth")
    if isinstance(value, float):
        if not math.isfinite(value):
            raise BridgeError(f"{where} contains a non-finite number")
        return
    if isinstance(value, int) and not isinstance(value, bool):
        if abs(value) > 10**15:
            raise BridgeError(f"{where} contains an unbounded integer")
        return
    if isinstance(value, str):
        if len(value) > MAX_STRING_LENGTH:
            raise BridgeError(f"{where} contains an overlong string")
        return
    if isinstance(value, list):
        if len(value) > MAX_JSON_NODES:
            raise BridgeError(f"{where} contains an oversized array")
        for index, item in enumerate(value):
            _finite_json(item, f"{where}[{index}]", depth=depth + 1, state=state)
        return
    if isinstance(value, dict):
        if len(value) > 2048:
            raise BridgeError(f"{where} contains an oversized object")
        for key, item in value.items():
            if not isinstance(key, str) or len(key) > MAX_STRING_LENGTH:
                raise BridgeError(f"{where} contains an invalid object key")
            _finite_json(item, f"{where}.{key}", depth=depth + 1, state=state)
        return
    if value is not None and not isinstance(value, bool):
        raise BridgeError(f"{where} contains an unsupported JSON value")


def _load_json(path: Path, where: str) -> tuple[Any, bytes]:
    _regular_file(path, where)
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise BridgeError(f"could not read {where}") from exc
    if len(data) > MAX_JSON_BYTES:
        raise BridgeError(f"{where} exceeds the bounded JSON size")
    try:
        text = data.decode("utf-8")
        value = json.loads(text, object_pairs_hook=_object_pairs, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise BridgeError(f"{where} is not valid finite UTF-8 JSON") from exc
    _finite_json(value, where)
    return value, data


def _object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _regular_file(path: Path, where: str) -> None:
    try:
        info = path.lstat()
    except OSError as exc:
        raise BridgeError(f"{where} is unavailable") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise BridgeError(f"{where} must be a regular non-symlink file")


def _directory(path: Path, where: str) -> None:
    try:
        info = path.lstat()
    except OSError as exc:
        raise BridgeError(f"{where} is unavailable") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise BridgeError(f"{where} must be a regular non-symlink directory")


def _obj(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise BridgeError(f"{where} must be an object")
    return value


def _list(value: Any, where: str, *, maximum: int) -> list[Any]:
    if not isinstance(value, list) or len(value) > maximum:
        raise BridgeError(f"{where} must be a bounded array")
    return value


def _text(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value or len(value) > MAX_STRING_LENGTH:
        raise BridgeError(f"{where} must be a bounded non-empty string")
    return value


def _vector(value: Any, where: str, length: int = 3) -> tuple[float, ...]:
    if not isinstance(value, list) or len(value) != length:
        raise BridgeError(f"{where} must be a finite {length}-vector")
    result: list[float] = []
    for index, item in enumerate(value):
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise BridgeError(f"{where}[{index}] must be numeric")
        number = float(item)
        if not math.isfinite(number):
            raise BridgeError(f"{where}[{index}] must be finite")
        result.append(number)
    return tuple(result)


def _address(value: Any, where: str, *, kind: str | None = None) -> tuple[tuple[str, tuple[str, ...], str, str], dict[str, Any]]:
    item = _obj(value, where)
    if set(item) != {"namespace", "anchors", "kind", "role"}:
        raise BridgeError(f"{where} has an invalid address shape")
    namespace = _text(item["namespace"], f"{where}.namespace")
    anchors_raw = item["anchors"]
    if not isinstance(anchors_raw, list) or len(anchors_raw) > 4:
        raise BridgeError(f"{where}.anchors is invalid")
    anchors = tuple(_text(anchor, f"{where}.anchors[{index}]") for index, anchor in enumerate(anchors_raw))
    if len(set(anchors)) != len(anchors):
        raise BridgeError(f"{where}.anchors contains duplicates")
    address_kind = _text(item["kind"], f"{where}.kind")
    role = _text(item["role"], f"{where}.role")
    if kind is not None and address_kind != kind:
        raise BridgeError(f"{where}.kind must be {kind}")
    key = (namespace, anchors, address_kind, role)
    normalized = {"namespace": namespace, "anchors": list(anchors), "kind": address_kind, "role": role}
    return key, normalized


def _address_json(key: tuple[str, tuple[str, ...], str, str]) -> dict[str, Any]:
    return {"namespace": key[0], "anchors": list(key[1]), "kind": key[2], "role": key[3]}


def _parse_frame(value: Any, where: str) -> None:
    frame = _obj(value, where)
    if set(frame) != {"translation", "rotation_xyzw"}:
        raise BridgeError(f"{where} has an invalid frame shape")
    _vector(frame["translation"], f"{where}.translation", 3)
    _vector(frame["rotation_xyzw"], f"{where}.rotation_xyzw", 4)


def _validate_structure(value: Any) -> dict[str, Any]:
    root = _obj(value, "inspect-structure result")
    required = {"format", "operation", "stage", "status", "processing_complete", "diagnostics_complete", "diagnostics", "summary", "graph"}
    if set(root) != required:
        raise BridgeError("inspect-structure result has unexpected or missing fields")
    if root["format"] != STRUCTURE_FORMAT or root["operation"] != "inspect-structure" or root["stage"] != "structural-validation" or root["status"] != "success":
        raise BridgeError("inspect-structure result is not a successful structural inspection")
    if root["processing_complete"] is not True or root["diagnostics_complete"] is not True or root["diagnostics"] != []:
        raise BridgeError("inspect-structure success flags or diagnostics are invalid")
    graph = _obj(root["graph"], "inspect-structure.graph")
    required_graph = {"projection", "contract", "source", "basis", "profiles", "extensions", "modules", "parts", "joints", "sockets", "attachments", "landmarks", "dimensions", "frames", "regions", "capabilities", "fields"}
    if set(graph) != required_graph or graph["projection"] != "source-preserving-provisional-structural-debug":
        raise BridgeError("inspect-structure.graph has an unsupported projection")
    source = _obj(graph["source"], "inspect-structure.graph.source")
    document = _text(source.get("document"), "inspect-structure.graph.source.document")
    namespace = _text(source.get("namespace"), "inspect-structure.graph.source.namespace")
    parts = _list(graph["parts"], "inspect-structure.graph.parts", maximum=MAX_PARTS)
    if not parts:
        raise BridgeError("inspect-structure.graph.parts is empty")
    part_map: dict[tuple[str, tuple[str, ...], str, str], dict[str, Any]] = {}
    parent_map: dict[tuple[str, tuple[str, ...], str, str], tuple[str, tuple[str, ...], str, str] | None] = {}
    for index, raw in enumerate(parts):
        item = _obj(raw, f"inspect-structure.graph.parts[{index}]")
        if set(item) != {"address", "containment", "placement"}:
            raise BridgeError(f"inspect-structure.graph.parts[{index}] has invalid fields")
        key, address = _address(item["address"], f"inspect-structure.graph.parts[{index}].address", kind="part")
        if key[0] != namespace or key in part_map:
            raise BridgeError("structural Part addresses are not unique or do not match source namespace")
        containment = _obj(item["containment"], f"inspect-structure.graph.parts[{index}].containment")
        if set(containment) == {"root"}:
            if containment["root"] is not True:
                raise BridgeError("structural root containment is invalid")
            parent = None
        elif set(containment) == {"parent"}:
            parent, _ = _address(containment["parent"], f"inspect-structure.graph.parts[{index}].containment.parent", kind="part")
            if parent[0] != namespace:
                raise BridgeError("structural parent namespace differs from source")
        else:
            raise BridgeError("structural Part containment is invalid")
        placement = _obj(item["placement"], f"inspect-structure.graph.parts[{index}].placement")
        if set(placement) != {"translation", "rotation_xyzw"}:
            raise BridgeError("structural Part placement is invalid")
        _vector(placement["translation"], "structural Part translation", 3)
        _vector(placement["rotation_xyzw"], "structural Part rotation", 4)
        part_map[key] = address
        parent_map[key] = parent
    roots = [key for key, parent in parent_map.items() if parent is None]
    if len(roots) != 1:
        raise BridgeError("structural Part containment must have exactly one root")
    for key, parent in parent_map.items():
        seen: set[tuple[str, tuple[str, ...], str, str]] = set()
        current = key
        while current is not None:
            if current in seen:
                raise BridgeError("structural Part containment contains a cycle")
            seen.add(current)
            if current not in parent_map:
                raise BridgeError("structural Part containment references an unknown parent")
            current = parent_map[current]
    joints = _list(graph["joints"], "inspect-structure.graph.joints", maximum=MAX_JOINTS)
    if not joints:
        raise BridgeError("structural graph has no semantic Joints for a bridge slice")
    joint_map: dict[tuple[str, tuple[str, ...], str, str], dict[str, Any]] = {}
    for index, raw in enumerate(joints):
        item = _obj(raw, f"inspect-structure.graph.joints[{index}]")
        required_joint = {"address", "proximal", "distal", "proximal_frame", "distal_frame"}
        if set(item) != required_joint:
            raise BridgeError(f"inspect-structure.graph.joints[{index}] has invalid fields")
        key, address = _address(item["address"], f"inspect-structure.graph.joints[{index}].address", kind="joint")
        if key[0] != namespace or key in joint_map:
            raise BridgeError("semantic Joint addresses are not unique or do not match source namespace")
        proximal, proximal_json = _address(item["proximal"], f"inspect-structure.graph.joints[{index}].proximal", kind="part")
        distal, distal_json = _address(item["distal"], f"inspect-structure.graph.joints[{index}].distal", kind="part")
        if proximal == distal or proximal not in part_map or distal not in part_map:
            raise BridgeError("semantic Joint endpoints are not known distinct source Parts")
        _parse_frame(item["proximal_frame"], f"joint[{index}].proximal_frame")
        _parse_frame(item["distal_frame"], f"joint[{index}].distal_frame")
        joint_map[key] = {"address": address, "proximal": proximal_json, "distal": distal_json, "proximal_key": proximal, "distal_key": distal}
    incoming_joint_by_part: dict[
        tuple[str, tuple[str, ...], str, str],
        tuple[str, tuple[str, ...], str, str],
    ] = {}
    for joint_key, joint in joint_map.items():
        distal = joint["distal_key"]
        if parent_map[distal] != joint["proximal_key"]:
            raise BridgeError("semantic Joint endpoints do not match immediate Part containment")
        if distal in incoming_joint_by_part:
            raise BridgeError("a non-root Part has more than one incoming semantic Joint")
        incoming_joint_by_part[distal] = joint_key
    if roots[0] in incoming_joint_by_part or set(incoming_joint_by_part) != set(part_map) - {roots[0]}:
        raise BridgeError("semantic Joints do not cover every non-root Part exactly once")
    return {
        "source": {"document": document, "namespace": namespace},
        "parts": part_map,
        "parents": parent_map,
        "root": roots[0],
        "joints": joint_map,
        "incoming_joint_by_part": incoming_joint_by_part,
    }


def _validate_form(value: Any, selected: str, *, structure: dict[str, Any], form_hash: str) -> dict[str, Any]:
    root = _obj(value, "inspect-provisional-form result")
    required = {"format", "operation", "status", "stage", "processing_complete", "diagnostics_complete", "diagnostics", "source", "reference_scale", "authored_dimensions", "authored_landmarks", "authored_frames", "authored_torso_profile", "authored_head_neck_profile", "authored_arm_profile", "authored_leg_profile", "authored_foot_profile", "variants", "limitations"}
    if set(root) != required or root["format"] != SOURCE_FORMAT or root["operation"] != "inspect-provisional-form" or root["status"] != "success" or root["stage"] != "provisional-form":
        raise BridgeError("inspect-provisional-form result is not successful v11 input")
    if root["processing_complete"] is not True or root["diagnostics_complete"] is not True or root["diagnostics"] != []:
        raise BridgeError("inspect-provisional-form success flags or diagnostics are invalid")
    source = _obj(root["source"], "inspect-provisional-form.source")
    if set(source) != {"document", "namespace", "resource_profile_id"}:
        raise BridgeError("inspect-provisional-form.source has invalid fields")
    document = _text(source["document"], "form source document")
    namespace = _text(source["namespace"], "form source namespace")
    if source["resource_profile_id"] != "ck.resource.body.r2" or document != structure["source"]["document"] or namespace != structure["source"]["namespace"]:
        raise BridgeError("structure and provisional-form source lineage disagrees")
    for name in ("reference_scale", "authored_dimensions", "authored_landmarks", "authored_frames", "authored_torso_profile", "authored_head_neck_profile", "authored_arm_profile", "authored_leg_profile", "authored_foot_profile", "limitations"):
        if name not in root:
            raise BridgeError(f"form field {name} is missing")
    variants = _list(root["variants"], "form variants", maximum=MAX_VARIANTS)
    if not variants:
        raise BridgeError("form variants are empty")
    by_id: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(variants):
        item = _obj(raw, f"form variants[{index}]")
        required_variant = {"id", "profile_id", "provenance", "descriptors", "torso_profile", "head_neck_profile", "arm_profile", "leg_profile", "foot_profile"}
        if set(item) != required_variant:
            raise BridgeError(f"form variants[{index}] has unexpected or missing fields")
        variant_id = _text(item["id"], f"form variants[{index}].id")
        if variant_id != item["profile_id"] or variant_id in by_id or "/" in variant_id or "\\" in variant_id:
            raise BridgeError("form variant/profile identity is invalid")
        descriptors = _list(item["descriptors"], f"form variants[{index}].descriptors", maximum=MAX_DESCRIPTORS)
        if not descriptors:
            raise BridgeError("form variant descriptors are empty")
        descriptor_map: dict[tuple[str, tuple[str, ...], str, str], dict[str, Any]] = {}
        for descriptor_index, raw_descriptor in enumerate(descriptors):
            descriptor = _obj(raw_descriptor, f"form variants[{index}].descriptors[{descriptor_index}]")
            expected = {"descriptor_kind", "address", "parent", "placement_source", "reference_point", "dimension_roles", "profile_id", "source", "provenance", "shape"}
            if set(descriptor) != expected or descriptor["descriptor_kind"] != "display-only-form-descriptor" or descriptor["profile_id"] != variant_id or descriptor["source"] != "profile-derived-display":
                raise BridgeError("form descriptor format or profile lineage is invalid")
            key, address = _address(descriptor["address"], f"form descriptor[{descriptor_index}].address", kind="part")
            if key[0] != namespace or key in descriptor_map:
                raise BridgeError("form descriptor Part addresses are invalid or duplicated")
            if descriptor["parent"] is not None:
                parent, _ = _address(descriptor["parent"], f"form descriptor[{descriptor_index}].parent", kind="part")
                if parent[0] != namespace:
                    raise BridgeError("form descriptor parent namespace differs from source")
            _vector(descriptor["reference_point"], f"form descriptor[{descriptor_index}].reference_point")
            if not isinstance(descriptor["dimension_roles"], list) or any(not isinstance(role, str) or not role for role in descriptor["dimension_roles"]):
                raise BridgeError("form descriptor dimension roles are invalid")
            descriptor_map[key] = {"address": address, "reference_point": _vector(descriptor["reference_point"], "descriptor reference point")}
        if set(descriptor_map) != set(structure["parts"]):
            raise BridgeError(f"form variant {variant_id} does not contain the exact structural Part inventory")
        by_id[variant_id] = {"raw": item, "descriptors": descriptor_map}
    if selected not in by_id:
        raise BridgeError("selected profile/variant id is absent from the provisional-form result")
    return {"source": {"document": document, "namespace": namespace, "resource_profile_id": source["resource_profile_id"]}, "variants": by_id, "raw_hash": form_hash}


def _safe_relative(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise BridgeError(f"{where} is not a safe relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts) or str(path) != value:
        raise BridgeError(f"{where} contains path traversal")
    return value


def _scan_bundle(root: Path) -> tuple[set[str], set[str]]:
    files: set[str] = set()
    directories: set[str] = set()
    entry_count = 0
    def walk(directory: Path, relative: str, depth: int) -> None:
        nonlocal entry_count
        if depth > MAX_BUNDLE_DEPTH:
            raise BridgeError("successor surface bundle directory depth is unbounded")
        try:
            entries = sorted(os.scandir(directory), key=lambda entry: entry.name)
        except OSError as exc:
            raise BridgeError("could not scan successor surface bundle") from exc
        for entry in entries:
            entry_count += 1
            if entry_count > MAX_BUNDLE_ENTRIES:
                raise BridgeError("successor surface bundle has too many entries")
            entry_relative = f"{relative}/{entry.name}" if relative else entry.name
            try:
                info = entry.stat(follow_symlinks=False)
            except OSError as exc:
                raise BridgeError("could not stat successor surface bundle member") from exc
            if stat.S_ISLNK(info.st_mode):
                raise BridgeError(f"successor surface bundle contains a symlink: {entry_relative}")
            if stat.S_ISDIR(info.st_mode):
                directories.add(entry_relative)
                walk(Path(entry.path), entry_relative, depth + 1)
            elif stat.S_ISREG(info.st_mode):
                files.add(entry_relative)
            else:
                raise BridgeError(f"successor surface bundle contains a special file: {entry_relative}")
    walk(root, "", 0)
    return files, directories


def _hash_file(path: Path, where: str) -> tuple[str, int]:
    _regular_file(path, where)
    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("rb") as stream:
            while True:
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
                size += len(chunk)
                if size > MAX_PLY_BYTES:
                    raise BridgeError(f"{where} exceeds the bounded artifact size")
    except OSError as exc:
        raise BridgeError(f"could not hash {where}") from exc
    return digest.hexdigest(), size


def _parse_ply(path: Path, *, expected_sha256: str) -> dict[str, Any]:
    _regular_file(path, "successor surface.ply")
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise BridgeError("could not read successor surface.ply") from exc
    if hashlib.sha256(data).hexdigest() != expected_sha256:
        raise BridgeError("successor surface.ply changed after inventory validation")
    if len(data) > MAX_PLY_BYTES or not data.endswith(b"\n") or b"\r" in data or any(byte > 0x7F for byte in data):
        raise BridgeError("successor surface.ply is not bounded ASCII text")
    header_and_records = data.split(b"\n", 12)
    if len(header_and_records) != 13:
        raise BridgeError("successor surface.ply has an incomplete ASCII PLY header")
    lines = header_and_records[:12]
    records = header_and_records[12]
    if lines[:2] != [b"ply", b"format ascii 1.0"]:
        raise BridgeError("successor surface.ply has an invalid ASCII PLY header")
    if lines[3:9] != [b"property float x", b"property float y", b"property float z", b"property float nx", b"property float ny", b"property float nz"] or lines[10:12] != [b"property list uchar int vertex_indices", b"end_header"]:
        raise BridgeError("successor surface.ply has an unsupported property schema")
    def count(line: bytes, prefix: bytes, maximum: int, where: str) -> int:
        if not line.startswith(prefix):
            raise BridgeError(f"{where} has an invalid element count")
        raw = line[len(prefix):]
        if not raw or not raw.isdigit():
            raise BridgeError(f"{where} has a non-canonical count")
        value = int(raw)
        if value <= 0 or value > maximum:
            raise BridgeError(f"{where} is outside the bounded positive range")
        return value
    vertex_count = count(lines[2], b"element vertex ", MAX_PLY_VERTICES, "PLY vertex count")
    face_count = count(lines[9], b"element face ", MAX_PLY_FACES, "PLY face count")
    if (
        vertex_count > MAX_OUTPUT_VERTICES
        or records.count(b"\n") != vertex_count + face_count
    ):
        raise BridgeError("successor surface.ply has extra, missing, or oversized records")
    lines.extend(records[:-1].split(b"\n"))
    vertices: list[tuple[float, float, float]] = []
    normals: list[tuple[float, float, float]] = []
    for index in range(vertex_count):
        fields = lines[12 + index].split()
        if len(fields) != 6:
            raise BridgeError(f"PLY vertex[{index}] does not have six values")
        try:
            values = tuple(float(field.decode("ascii")) for field in fields)
        except (UnicodeDecodeError, ValueError) as exc:
            raise BridgeError(f"PLY vertex[{index}] is not numeric") from exc
        if not all(math.isfinite(item) for item in values) or math.sqrt(sum(item * item for item in values[3:])) <= MIN_RADIUS:
            raise BridgeError(f"PLY vertex[{index}] has non-finite values or an unusable normal")
        vertices.append(values[:3])
        normals.append(values[3:])
    faces: list[tuple[int, int, int]] = []
    face_keys: set[tuple[int, int, int]] = set()
    edge_counts: dict[tuple[int, int], int] = {}
    edge_directions: dict[tuple[int, int], int] = {}
    edge_faces: dict[tuple[int, int], list[int]] = {}
    union_parent = list(range(vertex_count))
    def find(index: int) -> int:
        while union_parent[index] != index:
            union_parent[index] = union_parent[union_parent[index]]
            index = union_parent[index]
        return index
    def union(left: int, right: int) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            union_parent[right_root] = left_root
    for index in range(face_count):
        fields = lines[12 + vertex_count + index].split()
        if len(fields) != 4 or fields[0] != b"3":
            raise BridgeError(f"PLY face[{index}] is not triangular")
        try:
            indices = tuple(int(field.decode("ascii")) for field in fields[1:])
        except (UnicodeDecodeError, ValueError) as exc:
            raise BridgeError(f"PLY face[{index}] has invalid indices") from exc
        if any(item < 0 or item >= vertex_count for item in indices) or len(set(indices)) != 3:
            raise BridgeError(f"PLY face[{index}] has invalid or duplicate indices")
        key = tuple(sorted(indices))
        if key in face_keys:
            raise BridgeError(f"PLY face[{index}] is a duplicate")
        face_keys.add(key)
        first, second, third = (vertices[item] for item in indices)
        cross = (
            (second[1] - first[1]) * (third[2] - first[2]) - (second[2] - first[2]) * (third[1] - first[1]),
            (second[2] - first[2]) * (third[0] - first[0]) - (second[0] - first[0]) * (third[2] - first[2]),
            (second[0] - first[0]) * (third[1] - first[1]) - (second[1] - first[1]) * (third[0] - first[0]),
        )
        if not math.isfinite(sum(item * item for item in cross)) or sum(item * item for item in cross) <= 1.0e-28:
            raise BridgeError(f"PLY face[{index}] is degenerate")
        faces.append(indices)
        for left, right in ((indices[0], indices[1]), (indices[1], indices[2]), (indices[2], indices[0])):
            edge = (left, right) if left < right else (right, left)
            direction = 1 if (left, right) == edge else -1
            edge_counts[edge] = edge_counts.get(edge, 0) + 1
            edge_faces.setdefault(edge, []).append(index)
            if edge_counts[edge] > 2 or (edge in edge_directions and edge_directions[edge] == direction):
                raise BridgeError("PLY topology has an edge with invalid winding or incidence")
            edge_directions[edge] = direction
            union(left, right)
    if any(value != 2 for value in edge_counts.values()) or len({find(index) for index in range(vertex_count)}) != 1:
        raise BridgeError("PLY topology is not one connected watertight surface")
    face_neighbors: list[set[int]] = [set() for _ in faces]
    for incident in edge_faces.values():
        if len(incident) != 2:
            raise BridgeError("PLY topology has a non-manifold edge")
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
        raise BridgeError("PLY topology contains shells connected only at vertices")
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
            raise BridgeError("PLY topology has a non-manifold vertex link")
        pending = [next(iter(link))]
        visited: set[int] = set()
        while pending:
            current = pending.pop()
            if current in visited:
                continue
            visited.add(current)
            pending.extend(link[current] - visited)
        if len(visited) != len(link):
            raise BridgeError("PLY topology has a disconnected vertex link")
    centroid = tuple(
        math.fsum(vertex[axis] for vertex in vertices) / vertex_count
        for axis in range(3)
    )
    centered = [
        tuple(item[axis] - centroid[axis] for axis in range(3))
        for item in vertices
    ]
    signed_six_volume = math.fsum(
        first[0] * (second[1] * third[2] - second[2] * third[1])
        + first[1] * (second[2] * third[0] - second[0] * third[2])
        + first[2] * (second[0] * third[1] - second[1] * third[0])
        for first, second, third in ((centered[a], centered[b], centered[c]) for a, b, c in faces)
    )
    if not math.isfinite(signed_six_volume) or signed_six_volume <= 0.0:
        raise BridgeError("PLY has no finite positive oriented signed volume")
    return {"vertices": vertices, "normals": normals, "faces": faces, "component_count": 1, "signed_volume": signed_six_volume / 6.0}


def _validate_metrics(metrics: Any, ply: dict[str, Any], where: str) -> None:
    item = _obj(metrics, where)
    required = {"vertex_count", "face_count", "component_count", "watertight", "finite_vertices", "finite_normals", "valid_indices", "signed_volume"}
    if not required.issubset(item):
        raise BridgeError(f"{where} does not contain the required success claims")
    if (
        item["vertex_count"] != len(ply["vertices"])
        or item["face_count"] != len(ply["faces"])
        or item["component_count"] != ply["component_count"]
        or item["watertight"] is not True
        or item["finite_vertices"] is not True
        or item["finite_normals"] is not True
        or item["valid_indices"] is not True
    ):
        raise BridgeError(f"{where} success claims do not match the validated PLY")
    signed_volume = item["signed_volume"]
    if isinstance(signed_volume, bool) or not isinstance(signed_volume, (int, float)) or not math.isfinite(float(signed_volume)) or float(signed_volume) <= 0.0:
        raise BridgeError(f"{where}.signed_volume is not a finite positive success claim")
    tolerance = max(1.0e-9 * ply["signed_volume"], 1.0e-12)
    if abs(float(signed_volume) - ply["signed_volume"]) > tolerance:
        raise BridgeError(f"{where}.signed_volume does not match the validated PLY")


def _validate_bundle(bundle: Path, form: dict[str, Any], form_bytes: bytes, selected: str) -> dict[str, Any]:
    _directory(bundle, "successor surface bundle")
    manifest_path = bundle / "successor-surface-manifest.json"
    manifest, manifest_bytes = _load_json(manifest_path, "successor surface manifest")
    root = _obj(manifest, "successor surface manifest")
    required = {"format", "status", "consumer_id", "source_format", "source", "shared_render_bounds", "canvas", "layout", "projections", "generator", "variants"}
    if set(root) != required or root["format"] != SUCCESSOR_FORMAT or root["status"] != "success" or root["source_format"] != SOURCE_FORMAT:
        raise BridgeError("successor surface manifest is not a successful v9 bundle")
    source = _obj(root["source"], "successor manifest.source")
    if not {"format", "sha256", "document", "namespace", "resource_profile_id"}.issubset(source) or source["format"] != SOURCE_FORMAT or source["sha256"] != hashlib.sha256(form_bytes).hexdigest() or source["document"] != form["source"]["document"] or source["namespace"] != form["source"]["namespace"] or source["resource_profile_id"] != form["source"]["resource_profile_id"]:
        raise BridgeError("successor bundle source lineage does not match provisional-form input")
    variants = _list(root["variants"], "successor manifest.variants", maximum=MAX_VARIANTS)
    if not variants:
        raise BridgeError("successor manifest has no variants")
    expected_files = {"successor-surface-manifest.json"}
    variant_records: dict[str, dict[str, Any]] = {}
    input_files: list[dict[str, Any]] = [{"kind": "successor-manifest", "path": "successor-surface-manifest.json", "sha256": hashlib.sha256(manifest_bytes).hexdigest(), "bytes": len(manifest_bytes)}]
    expected_kinds = ["ply", "semantic-sidecar", "metrics", "successor-consumer-sidecar", "guide-skin-composite-png"]
    for index, raw_variant in enumerate(variants):
        variant = _obj(raw_variant, f"successor manifest.variants[{index}]")
        if set(variant) != {"id", "profile_id", "source_variant_sha256", "metrics", "inventory"}:
            raise BridgeError("successor manifest variant has unexpected or missing fields")
        variant_id = _text(variant["id"], "successor variant id")
        if variant_id != variant["profile_id"] or variant_id in variant_records or "/" in variant_id or "\\" in variant_id:
            raise BridgeError("successor variant/profile identity is invalid")
        if variant_id not in form["variants"]:
            raise BridgeError("successor variant is absent from provisional-form input")
        expected_variant_hash = hashlib.sha256(_canonical(form["variants"][variant_id]["raw"])).hexdigest()
        if variant["source_variant_sha256"] != expected_variant_hash:
            raise BridgeError(f"successor variant {variant_id} does not bind its producer variant")
        inventory = _list(variant["inventory"], f"successor variant {variant_id}.inventory", maximum=5)
        if [entry.get("kind") if isinstance(entry, dict) else None for entry in inventory] != expected_kinds:
            raise BridgeError(f"successor variant {variant_id} inventory order is invalid")
        paths = {
            "ply": f"{variant_id}/surface.ply",
            "semantic-sidecar": f"{variant_id}/semantic.json",
            "metrics": f"{variant_id}/metrics.json",
            "successor-consumer-sidecar": f"{variant_id}/successor.json",
            "guide-skin-composite-png": f"{variant_id}/guide-skin-composite.png",
        }
        entries: dict[str, dict[str, Any]] = {}
        for entry_index, raw_entry in enumerate(inventory):
            entry = _obj(raw_entry, f"successor variant {variant_id}.inventory[{entry_index}]")
            kind = entry.get("kind")
            allowed_extra = {"width", "height", "views", "panels_per_view", "mode"} if kind == "guide-skin-composite-png" else set()
            if set(entry) != {"kind", "path", "sha256", "bytes"} | allowed_extra or entry["path"] != paths[kind] or kind in entries:
                raise BridgeError(f"successor variant {variant_id} inventory entry is invalid")
            rel = _safe_relative(entry["path"], "successor inventory path")
            if rel != paths[kind] or rel in expected_files:
                raise BridgeError("successor inventory path is not canonical")
            if not isinstance(entry["sha256"], str) or len(entry["sha256"]) != 64 or any(char not in "0123456789abcdef" for char in entry["sha256"]) or type(entry["bytes"]) is not int or entry["bytes"] < 0:
                raise BridgeError("successor inventory hash or size is invalid")
            artifact = bundle / rel
            actual_hash, actual_size = _hash_file(artifact, f"successor artifact {rel}")
            if actual_hash != entry["sha256"] or actual_size != entry["bytes"]:
                raise BridgeError(f"successor inventory does not match {rel}")
            expected_files.add(rel)
            input_files.append({"kind": f"successor-{kind}", "path": rel, "sha256": actual_hash, "bytes": actual_size})
            entries[kind] = entry
        metrics_path = bundle / paths["metrics"]
        metrics_value, metrics_bytes = _load_json(metrics_path, f"successor {variant_id} metrics.json")
        if hashlib.sha256(metrics_bytes).hexdigest() != entries["metrics"]["sha256"]:
            raise BridgeError(f"successor {variant_id} metrics.json changed after inventory validation")
        if metrics_value != variant["metrics"]:
            raise BridgeError(f"successor variant {variant_id} manifest metrics do not match metrics.json")
        successor_value, successor_bytes = _load_json(bundle / paths["successor-consumer-sidecar"], f"successor {variant_id} successor.json")
        if hashlib.sha256(successor_bytes).hexdigest() != entries["successor-consumer-sidecar"]["sha256"]:
            raise BridgeError(f"successor {variant_id} successor.json changed after inventory validation")
        successor_obj = _obj(successor_value, f"successor {variant_id} successor.json")
        if successor_obj.get("format") != SUCCESSOR_FORMAT or successor_obj.get("variant_id") != variant_id or successor_obj.get("profile_id") != variant_id or successor_obj.get("source_variant_sha256") != expected_variant_hash:
            raise BridgeError(f"successor {variant_id} successor.json lineage is invalid")
        ply: dict[str, Any] | None = None
        semantic_value: dict[str, Any] | None = None
        if variant_id == selected:
            ply = _parse_ply(
                bundle / paths["ply"],
                expected_sha256=entries["ply"]["sha256"],
            )
            _validate_metrics(metrics_value, ply, f"successor {variant_id} metrics.json")
            semantic_raw, semantic_bytes = _load_json(bundle / paths["semantic-sidecar"], f"successor {variant_id} semantic.json")
            if hashlib.sha256(semantic_bytes).hexdigest() != entries["semantic-sidecar"]["sha256"]:
                raise BridgeError(f"successor {variant_id} semantic.json changed after inventory validation")
            semantic_value = _obj(semantic_raw, f"successor {variant_id} semantic.json")
            if set(semantic_value) != {"format", "source_format", "variant_id", "source_variant_sha256", "surface_sha256", "vertex_count", "source_node_labels", "attribution"} or semantic_value["format"] != SEMANTIC_FORMAT or semantic_value["source_format"] != SOURCE_FORMAT or semantic_value["variant_id"] != variant_id or semantic_value["source_variant_sha256"] != expected_variant_hash or semantic_value["surface_sha256"] != entries["ply"]["sha256"] or semantic_value["attribution"] != "every recipe component resolves to its source descriptor owner; no synthetic node identity is emitted":
                raise BridgeError("successor semantic sidecar format or boundary is invalid")
            labels = _list(semantic_value["source_node_labels"], "semantic source_node_labels", maximum=MAX_OUTPUT_VERTICES)
            if semantic_value["vertex_count"] != len(ply["vertices"]) or len(labels) != len(ply["vertices"]):
                raise BridgeError("semantic label count does not match PLY vertex order")
            known = set(form["variants"][selected]["descriptors"])
            for label_index, label in enumerate(labels):
                key, _ = _address(label, f"semantic source_node_labels[{label_index}]", kind="part")
                if key not in known or key not in set(form["variants"][selected]["descriptors"]):
                    raise BridgeError("semantic label is not a known producer source Part address")
        variant_records[variant_id] = {"manifest": variant, "entries": entries, "ply": ply, "semantic": semantic_value}
    files, directories = _scan_bundle(bundle)
    expected_directories = set(variant_records)
    if files != expected_files or directories != expected_directories:
        raise BridgeError("successor surface bundle contains unlisted, missing, or nested artifacts")
    if selected not in variant_records:
        raise BridgeError("selected profile/variant id is absent from successor surface bundle")
    input_files.sort(key=lambda item: (item["kind"], item["path"]))
    return {"manifest": root, "manifest_hash": hashlib.sha256(manifest_bytes).hexdigest(), "variant": variant_records[selected], "input_files": input_files}


def _distance_to_segment(point: tuple[float, float, float], start: tuple[float, float, float], end: tuple[float, float, float]) -> float:
    direction = tuple(end[axis] - start[axis] for axis in range(3))
    length_squared = sum(item * item for item in direction)
    if not math.isfinite(length_squared) or length_squared <= MIN_SEGMENT_LENGTH**2:
        raise BridgeError("bone segment is zero-length or non-finite")
    offset = tuple(point[axis] - start[axis] for axis in range(3))
    parameter = max(0.0, min(1.0, sum(offset[axis] * direction[axis] for axis in range(3)) / length_squared))
    nearest = tuple(start[axis] + parameter * direction[axis] for axis in range(3))
    distance = math.sqrt(sum((point[axis] - nearest[axis]) ** 2 for axis in range(3)))
    if not math.isfinite(distance):
        raise BridgeError("point-to-bone distance is non-finite")
    return distance


def _build_candidate(structure: dict[str, Any], form: dict[str, Any], bundle: dict[str, Any], selected: str, identity: dict[str, Any], *, candidate_profile_id: str = "synthetic-profile") -> dict[str, Any]:
    descriptors = form["variants"][selected]["descriptors"]
    joints = structure["joints"]
    ordered_joint_keys = sorted(joints)
    root_key = structure["root"]
    if not ordered_joint_keys:
        raise BridgeError("cannot derive a source-Part root bone without a semantic Joint")

    vertex_points = [tuple(point) for point in bundle["variant"]["ply"]["vertices"]]
    labels = [
        _address(raw, "semantic label", kind="part")[0]
        for raw in bundle["variant"]["semantic"]["source_node_labels"]
    ]
    root_vertices = [point for point, label in zip(vertex_points, labels) if label == root_key]
    if len(root_vertices) < 2:
        raise BridgeError("source root Part has insufficient owned surface vertices for a root bone")
    root_centroid = tuple(
        math.fsum(point[axis] for point in root_vertices) / len(root_vertices)
        for axis in range(3)
    )
    root_minimum = tuple(min(point[axis] for point in root_vertices) for axis in range(3))
    root_maximum = tuple(max(point[axis] for point in root_vertices) for axis in range(3))
    root_axis = max(range(3), key=lambda axis: root_maximum[axis] - root_minimum[axis])
    root_start = list(root_centroid)
    root_end = list(root_centroid)
    root_start[root_axis] = root_minimum[root_axis]
    root_end[root_axis] = root_maximum[root_axis]
    root_length = math.dist(root_start, root_end)
    if not math.isfinite(root_length) or root_length <= MIN_SEGMENT_LENGTH:
        raise BridgeError("source root Part owned surface cannot define a nondegenerate root bone")

    bone_ids = {
        joint_key: "bone-joint-"
        + hashlib.sha256(_canonical(_address_json(joint_key))).hexdigest()[:16]
        for joint_key in ordered_joint_keys
    }
    joint_internal: list[dict[str, Any]] = []
    for joint_key in ordered_joint_keys:
        joint = joints[joint_key]
        start = descriptors[joint["proximal_key"]]["reference_point"]
        end = descriptors[joint["distal_key"]]["reference_point"]
        length = math.dist(start, end)
        if not math.isfinite(length) or length <= MIN_SEGMENT_LENGTH:
            raise BridgeError("a semantic Joint produced a zero-length or non-finite bone segment")
        parent_joint = structure["incoming_joint_by_part"].get(joint["proximal_key"])
        parent = bone_ids[parent_joint] if parent_joint is not None else "bone-source-part-root"
        joint_internal.append({
            "id": bone_ids[joint_key],
            "kind": "derived-joint",
            "parent": parent,
            "joint": joint["address"],
            "proximal": joint["proximal"],
            "distal": joint["distal"],
            "a": list(start),
            "b": list(end),
            "length": length,
            "owned_part": joint["distal_key"],
            "source_parts": [joint["proximal_key"], joint["distal_key"]],
        })
    root_bone = {
        "id": "bone-source-part-root",
        "kind": "synthetic-source-part-root",
        "parent": None,
        "source_part": _address_json(root_key),
        "a": root_start,
        "b": root_end,
        "length": root_length,
        "owned_part": root_key,
        "source_parts": [root_key],
    }
    bones = [root_bone, *joint_internal]
    by_id = {bone["id"]: bone for bone in bones}
    for bone in bones:
        parent = bone["parent"]
        if parent is not None and parent not in by_id:
            raise BridgeError("derived hierarchy references an unknown parent bone")
        seen: set[str] = set()
        current: str | None = bone["id"]
        while current is not None:
            if current in seen:
                raise BridgeError("derived hierarchy contains a cycle")
            seen.add(current)
            current = by_id[current]["parent"]

    eligible_by_label: dict[tuple[str, tuple[str, ...], str, str], list[dict[str, Any]]] = {}
    for label in set(labels):
        candidates = [bone for bone in joint_internal if label in bone["source_parts"]]
        if label == root_key:
            candidates.append(root_bone)
        candidates.sort(key=lambda bone: bone["id"])
        if not candidates:
            raise BridgeError("a semantic surface owner has no incident candidate bone")
        eligible_by_label[label] = candidates

    influence_rows: list[list[dict[str, Any]]] = []
    primary_bone_ids: list[str] = []
    for index, point in enumerate(vertex_points):
        scored = sorted((
            (_distance_to_segment(point, tuple(bone["a"]), tuple(bone["b"])), bone)
            for bone in eligible_by_label[labels[index]]
        ), key=lambda item: (item[0], item[1]["id"]))[:MAX_INFLUENCES]
        raw_weights = [1.0 / (distance + 1.0e-9) for distance, _ in scored]
        total = math.fsum(raw_weights)
        if not math.isfinite(total) or total <= 0.0:
            raise BridgeError("vertex influence rule produced no finite positive weight")
        influences = [
            {"bone_id": bone["id"], "weight": raw / total}
            for raw, (_, bone) in zip(raw_weights, scored)
        ]
        if not influences or len(influences) > MAX_INFLUENCES or abs(
            math.fsum(item["weight"] for item in influences) - 1.0
        ) > 1.0e-12:
            raise BridgeError("vertex influence coverage is incomplete or not normalized")
        influence_rows.append(influences)
        primary_bone_ids.append(influences[0]["bone_id"])

    proxies: list[dict[str, Any]] = []
    for bone in bones:
        indices = [
            index
            for index, primary_bone_id in enumerate(primary_bone_ids)
            if primary_bone_id == bone["id"]
        ]
        if not indices:
            continue
        start, end = tuple(bone["a"]), tuple(bone["b"])
        radius = max(_distance_to_segment(vertex_points[index], start, end) for index in indices)
        if not math.isfinite(radius) or radius <= MIN_RADIUS:
            raise BridgeError(f"bone {bone['id']} has a degenerate surface-derived capsule radius")
        proxies.append({
            "bone_id": bone["id"],
            "kind": "capsule",
            "a": list(start),
            "b": list(end),
            "radius": radius,
            "owned_part": _address_json(bone["owned_part"]),
            "partition_vertex_count": len(indices),
            "partition_rule": "nearest eligible weighted bone, then ascending derived bone id",
            "radius_rule": "maximum point-to-segment distance over the bone's complete primary-influence partition",
        })

    semantic_counts: dict[
        tuple[str, tuple[str, ...], str, str],
        int,
    ] = {}
    for label in labels:
        semantic_counts[label] = semantic_counts.get(label, 0) + 1
    missing_semantic_parts = sorted(set(descriptors) - set(semantic_counts))

    for bone in bones:
        bone["owned_part"] = _address_json(bone["owned_part"])
        bone["source_parts"] = [_address_json(key) for key in bone["source_parts"]]
    mapping = [{"joint": joints[key]["address"], "bone_id": bone_ids[key]} for key in ordered_joint_keys]
    checks = {
        "rooted_acyclic_hierarchy": True,
        "complete_joint_to_bone_mapping": len(mapping) == len(joints) and len({item["bone_id"] for item in mapping}) == len(joints),
        "finite_nonnegative_normalized_weights": all(item["weight"] >= 0.0 and math.isfinite(item["weight"]) for row in influence_rows for item in row) and all(abs(math.fsum(item["weight"] for item in row) - 1.0) <= 1.0e-12 for row in influence_rows),
        "full_vertex_coverage": len(influence_rows) == len(vertex_points) and all(influence_rows),
        "max_four_influences": all(len(row) <= MAX_INFLUENCES for row in influence_rows),
        "every_bone_has_positive_influence": {
            item["bone_id"]
            for row in influence_rows
            for item in row
            if item["weight"] > 0.0
        } == set(by_id),
        "complete_proxy_vertex_partition": (
            len(primary_bone_ids) == len(vertex_points)
            and sum(item["partition_vertex_count"] for item in proxies) == len(vertex_points)
            and {item["bone_id"] for item in proxies} == set(primary_bone_ids)
        ),
        "finite_non_degenerate_capsules": bool(proxies) and all(math.isfinite(item["radius"]) and item["radius"] > MIN_RADIUS for item in proxies),
    }
    if not all(checks.values()):
        raise BridgeError("one or more objective bridge gates did not pass")
    return {
        "format": BRIDGE_FORMAT,
        "status": "success",
        "boundary": "candidate-scoped disposable structural evidence; no pose, IK, contact, runtime, anatomy, engine, or production format",
        "algorithm": {"revision": ALGORITHM_REVISION, "configuration_revision": CONFIGURATION_REVISION},
        "identity": identity,
        "source": {"document": form["source"]["document"], "namespace": form["source"]["namespace"], "format": SOURCE_FORMAT, "candidate_profile_id": candidate_profile_id, "surface_variant_id": selected},
        "hierarchy": {"bone_count": len(bones), "synthetic_root_bone_id": "bone-source-part-root", "bones": bones, "joint_address_to_bone": mapping, "parent_rule": "a Joint bone uses the unique incoming Joint bone of its proximal Part; root-child Joints attach to the source-Part root bone"},
        "semantic_coverage": {
            "authority": "inventory-bound generated per-vertex source-owner winners; not independently recomputed by this bridge",
            "observed_source_parts": [
                {
                    "part": _address_json(key),
                    "vertex_count": semantic_counts[key],
                }
                for key in sorted(semantic_counts)
            ],
            "unobserved_source_parts": [
                _address_json(key) for key in missing_semantic_parts
            ],
        },
        "weights": {"vertex_count": len(vertex_points), "max_influences": MAX_INFLUENCES, "influences": influence_rows, "rule": {"semantic_label_role": "authoritative generated source-owner eligibility, never bone identity", "owner": "all derived bones incident to the labeled source Part; the synthetic root is eligible only for the source root Part", "distance": "Euclidean point-to-segment distance", "tie_break": "ascending derived bone id", "normalization": "inverse(distance + 1e-9), normalized over the first four sorted candidates"}},
        "proxies": proxies,
        "checks": checks,
        "pose": {"status": "later-slice", "note": "No pose payload or posed surface is produced by this first bridge slice; the shared-pose gallery remains a later checkpoint."},
    }


def _atomic_publish_no_replace(source: Path, destination: Path) -> None:
    if os.name != "posix":
        raise BridgeError("atomic no-replace directory publication requires Linux/WSL")
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    if renameat2 is None:
        raise BridgeError("Linux/WSL renameat2 no-replace publication is unavailable")
    renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    renameat2.restype = ctypes.c_int
    result = renameat2(-100, os.fsencode(source), -100, os.fsencode(destination), 1)
    if result != 0:
        error = ctypes.get_errno()
        if error == errno.EEXIST:
            raise FileExistsError(str(destination))
        if error in {
            errno.EINVAL,
            errno.ENOSYS,
            errno.EXDEV,
            getattr(errno, "EOPNOTSUPP", errno.EINVAL),
        }:
            raise BridgeError(
                "output parent filesystem does not support atomic Linux no-replace directory publication"
            )
        raise OSError(error, os.strerror(error), str(destination))


def build(structure_path: Path, form_path: Path, bundle_path: Path, candidate_profile_id: str, surface_variant_id: str, output: Path) -> dict[str, Any]:
    candidate_profile_id = _text(candidate_profile_id, "candidate profile id")
    surface_variant_id = _text(surface_variant_id, "surface variant id")
    structure_value, structure_bytes = _load_json(structure_path, "inspect-structure JSON")
    form_value, form_bytes = _load_json(form_path, "inspect-provisional-form v11 JSON")
    structure = _validate_structure(structure_value)
    form = _validate_form(form_value, surface_variant_id, structure=structure, form_hash=hashlib.sha256(form_bytes).hexdigest())
    if candidate_profile_id in form["variants"]:
        raise BridgeError("candidate profile id must not collide with a surface variant id")
    if not CANDIDATE_PROFILE_ID.fullmatch(candidate_profile_id):
        raise BridgeError("candidate profile id must be a restricted source-profile identifier")
    bundle = _validate_bundle(bundle_path, form, form_bytes, surface_variant_id)
    input_files = [
        {"kind": "inspect-structure", "path": "inspect-structure.json", "sha256": hashlib.sha256(structure_bytes).hexdigest(), "bytes": len(structure_bytes)},
        {"kind": "inspect-provisional-form", "path": "inspect-provisional-form.json", "sha256": hashlib.sha256(form_bytes).hexdigest(), "bytes": len(form_bytes)},
        *bundle["input_files"],
    ]
    input_files.sort(key=lambda item: (item["kind"], item["path"]))
    identity_basis = {"algorithm_revision": ALGORITHM_REVISION, "configuration_revision": CONFIGURATION_REVISION, "candidate_profile_id": candidate_profile_id, "surface_variant_id": surface_variant_id, "provenance_semantics": "exact bounded input bytes; logically equivalent re-encodings intentionally have distinct identity", "input_files": input_files}
    identity = {"candidate_sha256": _digest(IDENTITY_DOMAIN + ":candidate", identity_basis), "request_sha256": _digest(IDENTITY_DOMAIN + ":request", identity_basis), "basis": identity_basis}
    candidate = _build_candidate(structure, form, bundle, surface_variant_id, identity, candidate_profile_id=candidate_profile_id)
    _directory(output.parent, "output parent")
    try:
        output.lstat()
    except FileNotFoundError:
        pass
    except OSError as exc:
        raise BridgeError("could not inspect output path") from exc
    else:
        raise BridgeError("refusing to overwrite existing output")
    stage = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=str(output.parent)))
    try:
        artifact_path = stage / BRIDGE_FILE
        artifact_bytes = _canonical(candidate) + b"\n"
        artifact_path.write_bytes(artifact_bytes)
        artifact_hash = hashlib.sha256(artifact_bytes).hexdigest()
        manifest = {"format": MANIFEST_FORMAT, "status": "success", "bridge_format": BRIDGE_FORMAT, "algorithm_revision": ALGORITHM_REVISION, "configuration_revision": CONFIGURATION_REVISION, "candidate_profile_id": candidate_profile_id, "surface_variant_id": surface_variant_id, "candidate_sha256": identity["candidate_sha256"], "request_sha256": identity["request_sha256"], "input_files": input_files, "inventory": [{"kind": "bridge-json", "path": BRIDGE_FILE, "sha256": artifact_hash, "bytes": len(artifact_bytes)}]}
        (stage / MANIFEST_FILE).write_bytes(_canonical(manifest) + b"\n")
        actual_files, actual_dirs = _scan_bundle(stage)
        if actual_files != {BRIDGE_FILE, MANIFEST_FILE} or actual_dirs:
            raise BridgeError("staging output does not match its explicit inventory")
        _atomic_publish_no_replace(stage, output)
        return {"candidate": candidate, "manifest": manifest}
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise BridgeError(f"usage error: {message}")


def _parser() -> argparse.ArgumentParser:
    parser = _Parser(description="Build a disposable neutral structural-embodiment bridge artifact")
    parser.add_argument("--inspect-structure", "--structure", "--structure-json", dest="structure", type=Path, required=True)
    parser.add_argument("--inspect-provisional-form", "--provisional-form", "--form", dest="form", type=Path, required=True)
    parser.add_argument("--surface-bundle", "--bundle", dest="bundle", type=Path, required=True)
    parser.add_argument("--candidate-profile-id", dest="candidate_profile", required=True)
    parser.add_argument("--surface-variant-id", "--variant-id", dest="surface_variant", required=True)
    parser.add_argument("--output", "--output-root", dest="output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        result = build(args.structure, args.form, args.bundle, args.candidate_profile, args.surface_variant, args.output)
    except (BridgeError, OSError, ValueError) as exc:
        message = str(exc).replace("\n", " ")[:240] or "bridge failed"
        print(json.dumps({"format": BRIDGE_FORMAT, "status": "failure", "error": message}, sort_keys=True, separators=(",", ":")), file=sys.stderr)
        return 2
    print(json.dumps({"format": BRIDGE_FORMAT, "status": "success", "candidate_sha256": result["manifest"]["candidate_sha256"], "output": str(args.output)}, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

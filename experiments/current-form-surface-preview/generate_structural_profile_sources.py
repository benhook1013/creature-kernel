#!/usr/bin/env python3
"""Generate experiment-local structural source-profile candidates.

The candidate JSON is the frozen data table.  This module contains one
selector-driven transform and the fail-closed checks around it; profile IDs do
not select code paths.  The generated body documents remain disposable source
inputs for the existing structural and provisional-form inspection CLIs.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import re
import stat
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

import structural_atomic_publish


HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[2]
DEFAULT_CANDIDATE = HERE.with_name("structural_profile_candidates.json")
DEFAULT_SOURCE = REPO_ROOT / "examples/body-documents/stylized-digitigrade-biped-authored-form.json"
HISTORICAL_FIXTURE_ROOT = HERE.parent / "historical" / "structural-embodiment-v1"
HISTORICAL_CANDIDATE = HISTORICAL_FIXTURE_ROOT / "structural_profile_candidates.json"
HISTORICAL_SOURCE = HISTORICAL_FIXTURE_ROOT / "stylized-digitigrade-biped-authored-form.json"
FORMAT = "creature-kernel.disposable-structural-profile-candidates.v1"
SOURCE_DOCUMENT_SUFFIX = "structural_profile"
DEFAULT_GENERATION_MODE = "active-five-profile"
HISTORICAL_GENERATION_MODE = "historical-structural-embodiment-v1"
PROFILE_COUNT = 5
STANDARD_NEUTRAL_PROFILE_ID = "standard_neutral_reference"
ACTIVE_PROFILE_IDS = (
    "standard_neutral_reference",
    "compact_broad_short_limb_large_head",
    "tall_narrow_long_legged",
    "slender_long_limb",
    "stocky_broad_chested",
)
HISTORICAL_PROFILE_IDS = (
    "compact_broad_short_limb_large_head",
    "tall_narrow_long_legged",
    "slender_long_limb",
    "stocky_broad_chested",
)
HISTORICAL_CANDIDATE_SHA256 = "68d6e808a21daad16e1d56716124fc96b021bc492adf5171ec4e155591f45336"
HISTORICAL_SOURCE_SHA256 = "faf02db965a2b7f6889dfb1cd58eb79befa9c536f58adca40b14ccc955eaf533"
MAX_SAFE_INTEGER = 10**9
MAX_JSON_BYTES = 1024 * 1024
MAX_OUTPUT_JSON_BYTES = MAX_JSON_BYTES
MAX_JSON_NODES = 100_000
MAX_JSON_DEPTH = 64
MAX_STRING_LENGTH = 65_536
IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")
PRESERVED_CONTROLS = [
    "body.landmarks[*].position",
    "body.frames[*].transform",
    "body.joints[*].proximal_frame",
    "body.joints[*].distal_frame",
    "body.sockets[*].interface_frame",
    "body.attachments[*].offset",
]


class ProfileGenerationError(ValueError):
    """The frozen candidate or its source cannot be safely transformed."""


def canonical_bytes(value: Any) -> bytes:
    try:
        return (
            json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise ProfileGenerationError("value is not canonical finite UTF-8 JSON") from exc


def canonical_source_bytes(value: Any) -> bytes:
    """Use compact canonical source bytes so the existing ordinary CLI limit is retained."""
    try:
        return (
            json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise ProfileGenerationError("source is not canonical finite UTF-8 JSON") from exc


def _profile_contract(mode: str) -> tuple[int, tuple[str, ...] | None]:
    if mode == DEFAULT_GENERATION_MODE:
        return PROFILE_COUNT, ACTIVE_PROFILE_IDS
    if mode == HISTORICAL_GENERATION_MODE:
        return len(HISTORICAL_PROFILE_IDS), HISTORICAL_PROFILE_IDS
    raise ProfileGenerationError(f"unsupported structural profile generation mode: {mode}")


def _historical_fixture_values() -> tuple[dict[str, Any], bytes, dict[str, Any], bytes]:
    candidate_path = _path_without_symlinks(HISTORICAL_CANDIDATE, "historical candidate fixture path")
    source_path = _path_without_symlinks(HISTORICAL_SOURCE, "historical source fixture path")
    candidate, candidate_bytes = load_json_with_bytes(candidate_path, "historical candidate fixture")
    source, source_bytes = load_json_with_bytes(source_path, "historical source fixture")
    if hashlib.sha256(candidate_bytes).hexdigest() != HISTORICAL_CANDIDATE_SHA256:
        raise ProfileGenerationError("historical candidate fixture bytes are not the frozen origin/main bytes")
    if hashlib.sha256(source_bytes).hexdigest() != HISTORICAL_SOURCE_SHA256:
        raise ProfileGenerationError("historical source fixture bytes are not the frozen origin/main bytes")
    return _object(candidate, "historical candidate fixture"), candidate_bytes, _object(source, "historical source fixture"), source_bytes


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ProfileGenerationError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def load_json_with_bytes(path: Path, label: str) -> tuple[Any, bytes]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ProfileGenerationError(f"could not read {label}: {path}") from exc
    if len(raw) > MAX_JSON_BYTES:
        raise ProfileGenerationError(f"{label} exceeds the bounded JSON size")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_strict_object,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise ProfileGenerationError(f"{label} is not finite UTF-8 JSON") from exc
    _finite(value, label)
    return value, raw


def load_json(path: Path, label: str) -> Any:
    return load_json_with_bytes(path, label)[0]


def _path_without_symlinks(path: Path, label: str) -> Path:
    """Return an absolute lexical path after rejecting existing symlink components."""
    try:
        candidate = Path(os.fspath(path))
        absolute = candidate if candidate.is_absolute() else Path.cwd() / candidate
    except (OSError, TypeError, ValueError) as exc:
        raise ProfileGenerationError(f"{label} is not a usable path") from exc
    current = Path(absolute.anchor)
    for component in absolute.parts[1:]:
        if component == ".":
            continue
        if component == "..":
            current = current.parent
            continue
        current /= component
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            continue
        except (OSError, ValueError) as exc:
            raise ProfileGenerationError(f"could not inspect {label}: {absolute}") from exc
        if stat.S_ISLNK(mode):
            raise ProfileGenerationError(f"{label} contains a symlinked path component: {current}")
    return current


def _finite(value: Any, where: str, *, depth: int = 0, state: list[int] | None = None) -> None:
    if state is None:
        state = [0]
    state[0] += 1
    if state[0] > MAX_JSON_NODES:
        raise ProfileGenerationError(f"{where} exceeds the bounded JSON node count")
    if depth > MAX_JSON_DEPTH:
        raise ProfileGenerationError(f"{where} exceeds the bounded JSON depth")
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ProfileGenerationError(f"{where} contains a non-finite number")
        return
    if isinstance(value, int) and not isinstance(value, bool):
        if abs(value) > MAX_SAFE_INTEGER:
            raise ProfileGenerationError(f"{where} contains an unsafe integer")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _finite(item, f"{where}[{index}]", depth=depth + 1, state=state)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str) or len(key) > MAX_STRING_LENGTH:
                raise ProfileGenerationError(f"{where} contains a non-string key")
            _finite(item, f"{where}.{key}", depth=depth + 1, state=state)
        return
    if isinstance(value, str) and len(value) > MAX_STRING_LENGTH:
        raise ProfileGenerationError(f"{where} contains an overlong string")
    if value is not None and not isinstance(value, (str, bool)):
        raise ProfileGenerationError(f"{where} contains an unsupported JSON value")


def _object(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProfileGenerationError(f"{where} must be an object")
    return value


def _list(value: Any, where: str) -> list[Any]:
    if not isinstance(value, list):
        raise ProfileGenerationError(f"{where} must be an array")
    return value


def _text(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value:
        raise ProfileGenerationError(f"{where} must be a non-empty string")
    return value


def _integer(value: Any, where: str, *, minimum: int = 0, maximum: int = MAX_SAFE_INTEGER) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProfileGenerationError(f"{where} must be an integer")
    if value < minimum or value > maximum:
        raise ProfileGenerationError(f"{where} is outside the safe integer range")
    return value


def _vector(value: Any, where: str, length: int = 3) -> list[int]:
    values = _list(value, where)
    if len(values) != length:
        raise ProfileGenerationError(f"{where} must have length {length}")
    return [_integer(item, f"{where}[{index}]", minimum=-MAX_SAFE_INTEGER, maximum=MAX_SAFE_INTEGER) for index, item in enumerate(values)]


def _address(value: Any, where: str, *, kind: str | None = None) -> dict[str, Any]:
    address = _object(value, where)
    if set(address) != {"anchors", "kind", "namespace", "role"}:
        raise ProfileGenerationError(f"{where} has an invalid address shape")
    namespace = _text(address["namespace"], f"{where}.namespace")
    anchors = _list(address["anchors"], f"{where}.anchors")
    if any(not isinstance(anchor, str) or not anchor for anchor in anchors):
        raise ProfileGenerationError(f"{where}.anchors contains an invalid identifier")
    address_kind = _text(address["kind"], f"{where}.kind")
    if kind is not None and address_kind != kind:
        raise ProfileGenerationError(f"{where}.kind must be {kind}")
    return {"namespace": namespace, "anchors": list(anchors), "kind": address_kind, "role": _text(address["role"], f"{where}.role")}


def address_key(address: dict[str, Any]) -> str:
    anchors = ",".join(address["anchors"])
    return f"{address['namespace']}|{address['kind']}|{anchors}|{address['role']}"


def parse_address_key(value: Any, where: str) -> str:
    key = _text(value, where)
    pieces = key.split("|")
    if len(pieces) != 4 or any(piece == "" for piece in (pieces[0], pieces[1], pieces[3])):
        raise ProfileGenerationError(f"{where} is not a typed address key")
    if pieces[2] and any(not anchor for anchor in pieces[2].split(",")):
        raise ProfileGenerationError(f"{where} contains an empty anchor")
    return key


def _require_keys(value: dict[str, Any], expected: Iterable[str], where: str) -> None:
    expected_set = set(expected)
    if set(value) != expected_set:
        missing = sorted(expected_set - set(value))
        extra = sorted(set(value) - expected_set)
        detail = []
        if missing:
            detail.append("missing " + ", ".join(missing))
        if extra:
            detail.append("unknown " + ", ".join(extra))
        raise ProfileGenerationError(f"{where} has invalid fields ({'; '.join(detail)})")


def _owner_pattern(value: Any, where: str) -> tuple[tuple[str, ...], str]:
    pattern = _object(value, where)
    _require_keys(pattern, ("anchors", "role"), where)
    anchors = tuple(_text(item, f"{where}.anchors[{index}]") for index, item in enumerate(_list(pattern["anchors"], f"{where}.anchors")))
    return anchors, _text(pattern["role"], f"{where}.role")


def _matches_dimension(dimension: dict[str, Any], selector: dict[str, Any]) -> bool:
    owner = dimension["owner"]
    pattern = (tuple(owner["anchors"]), owner["role"])
    owners = selector["owner_patterns"]
    if pattern not in owners:
        return False
    role = dimension["role"]
    if "role" in selector and role != selector["role"]:
        return False
    if "role_prefix" in selector and not role.startswith(selector["role_prefix"]):
        return False
    suffixes = selector.get("role_suffixes")
    return not suffixes or any(role.endswith(suffix) for suffix in suffixes)


def _round_permille(value: int, scale: int) -> int:
    product = value * scale
    quotient, remainder = divmod(product, 1000)
    if remainder > 500 or (remainder == 500 and quotient % 2):
        quotient += 1
    return quotient


def _rotation_paths(source: dict[str, Any]) -> list[tuple[str, list[Any]]]:
    body = _object(source["body"], "source.body")
    paths: list[tuple[str, list[Any]]] = []
    for collection, field in (("parts", "placement"), ("joints", "proximal_frame"), ("joints", "distal_frame"), ("sockets", "interface_frame"), ("attachments", "offset"), ("frames", "transform")):
        for index, record in enumerate(_list(body[collection], f"source.body.{collection}")):
            item = _object(record, f"source.body.{collection}[{index}]")
            frame = _object(item[field], f"source.body.{collection}[{index}].{field}")
            rotation = frame.get("rotation_xyzw")
            if not isinstance(rotation, list) or len(rotation) != 4:
                raise ProfileGenerationError(f"source.body.{collection}[{index}].{field}.rotation_xyzw is invalid")
            if any(not isinstance(number, (int, float)) or isinstance(number, bool) or not math.isfinite(float(number)) for number in rotation):
                raise ProfileGenerationError(f"source.body.{collection}[{index}].{field}.rotation_xyzw is unsafe")
            paths.append((f"body.{collection}[{index}].{field}.rotation_xyzw", list(rotation)))
    return paths


def _walk_path(value: dict[str, Any], path: str) -> Any:
    current: Any = value
    for component in path.split("."):
        if "[" in component:
            name, index_text = component[:-1].split("[")
            current = current[name][int(index_text)]
        else:
            current = current[component]
    return current


def _world_part_translations(source: dict[str, Any]) -> dict[str, tuple[int, int, int]]:
    body = _object(source["body"], "source.body")
    parts = _list(body["parts"], "source.body.parts")
    by_key: dict[str, dict[str, Any]] = {}
    parents: dict[str, str | None] = {}
    for index, raw in enumerate(parts):
        part = _object(raw, f"source.body.parts[{index}]")
        address = _address(part["address"], f"source.body.parts[{index}].address", kind="part")
        key = address_key(address)
        if key in by_key:
            raise ProfileGenerationError(f"duplicate source Part target: {key}")
        containment = _object(part["containment"], f"source.body.parts[{index}].containment")
        if set(containment) == {"root"}:
            if containment["root"] is not True:
                raise ProfileGenerationError("source root containment is not true")
            parent = None
        elif set(containment) == {"parent"}:
            parent_address = _address(containment["parent"], f"source.body.parts[{index}].containment.parent", kind="part")
            parent = address_key(parent_address)
        else:
            raise ProfileGenerationError(f"source.body.parts[{index}].containment is invalid")
        placement = _object(part["placement"], f"source.body.parts[{index}].placement")
        translation = _vector(placement["translation"], f"source.body.parts[{index}].placement.translation")
        _address(part["address"], f"source.body.parts[{index}].address", kind="part")
        by_key[key] = part
        parents[key] = parent
        part["placement"]["translation"] = translation
    roots = [key for key, parent in parents.items() if parent is None]
    if len(roots) != 1:
        raise ProfileGenerationError(f"source Part containment needs exactly one root, found {len(roots)}")
    if any(parent not in by_key for parent in parents.values() if parent is not None):
        raise ProfileGenerationError("source Part containment names an unknown parent")

    world: dict[str, tuple[int, int, int]] = {}

    def resolve(key: str, trail: set[str]) -> tuple[int, int, int]:
        if key in world:
            return world[key]
        if key in trail:
            raise ProfileGenerationError("source Part containment contains a cycle")
        trail.add(key)
        placement = by_key[key]["placement"]["translation"]
        parent = parents[key]
        if parent is None:
            result = tuple(placement)
        else:
            parent_world = resolve(parent, trail)
            result = tuple(parent_world[index] + placement[index] for index in range(3))
        trail.remove(key)
        world[key] = result
        return result

    for key in by_key:
        resolve(key, set())
    return world


def _check_attachment_equations(source: dict[str, Any], where: str) -> None:
    body = _object(source["body"], f"{where}.body")
    part_world = _world_part_translations(source)
    socket_world: dict[str, tuple[int, int, int]] = {}
    for index, raw in enumerate(_list(body["sockets"], f"{where}.body.sockets")):
        socket = _object(raw, f"{where}.body.sockets[{index}]")
        socket_address = _address(socket["address"], f"{where}.body.sockets[{index}].address", kind="socket")
        owner = _address(socket["owner"], f"{where}.body.sockets[{index}].owner", kind="part")
        owner_world = part_world.get(address_key(owner))
        if owner_world is None:
            raise ProfileGenerationError(f"{where} socket has an unknown Part owner")
        frame = _object(socket["interface_frame"], f"{where}.body.sockets[{index}].interface_frame")
        translation = _vector(frame["translation"], f"{where}.body.sockets[{index}].interface_frame.translation")
        key = address_key(socket_address)
        if key in socket_world:
            raise ProfileGenerationError(f"{where} has duplicate Socket target {key}")
        socket_world[key] = tuple(owner_world[axis] + translation[axis] for axis in range(3))
    for index, raw in enumerate(_list(body["attachments"], f"{where}.body.attachments")):
        attachment = _object(raw, f"{where}.body.attachments[{index}]")
        host = _address(attachment["host"], f"{where}.body.attachments[{index}].host", kind="socket")
        mating = _address(attachment["mating"], f"{where}.body.attachments[{index}].mating", kind="socket")
        host_world = socket_world.get(address_key(host))
        mating_world = socket_world.get(address_key(mating))
        if host_world is None or mating_world is None:
            raise ProfileGenerationError(f"{where} Attachment names an unknown Socket")
        offset = _object(attachment["offset"], f"{where}.body.attachments[{index}].offset")
        offset_translation = _vector(offset["translation"], f"{where}.body.attachments[{index}].offset.translation")
        if tuple(host_world[axis] + offset_translation[axis] for axis in range(3)) != mating_world:
            raise ProfileGenerationError(f"{where} Attachment equation failed: host_world + offset != mating_world")


def _validate_source_shape(source: dict[str, Any], candidate: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    _require_keys(source, ("basis", "body", "contract", "extensions", "profiles", "source"), "source")
    source_metadata = _object(source["source"], "source.source")
    _require_keys(source_metadata, ("dependencies", "document", "namespace"), "source.source")
    base_source = _object(candidate["base_source"], "candidate.base_source")
    if source_metadata["document"] != base_source["document"] or source_metadata["namespace"] != base_source["namespace"]:
        raise ProfileGenerationError("source identity does not match candidate.base_source")
    body = _object(source["body"], "source.body")
    parts = [_object(item, f"source.body.parts[{index}]") for index, item in enumerate(_list(body["parts"], "source.body.parts"))]
    dimensions = [_object(item, f"source.body.dimensions[{index}]") for index, item in enumerate(_list(body["dimensions"], "source.body.dimensions"))]
    part_keys: dict[str, dict[str, Any]] = {}
    for index, part in enumerate(parts):
        address = _address(part["address"], f"source.body.parts[{index}].address", kind="part")
        key = address_key(address)
        if key in part_keys:
            raise ProfileGenerationError(f"source has duplicate Part target {key}")
        part_keys[key] = part
        placement = _object(part["placement"], f"source.body.parts[{index}].placement")
        _vector(placement["translation"], f"source.body.parts[{index}].placement.translation")
        rotation = placement.get("rotation_xyzw")
        if not isinstance(rotation, list) or len(rotation) != 4 or any(not isinstance(item, (int, float)) or isinstance(item, bool) or not math.isfinite(float(item)) for item in rotation):
            raise ProfileGenerationError(f"source Part {key} has an unsafe rotation")
    _world_part_translations(source)
    _check_attachment_equations(source, "source")
    rotation_paths = _rotation_paths(source)
    if any(rotation != [0, 0, 0, 1] for _, rotation in rotation_paths):
        raise ProfileGenerationError("this candidate slice admits the authored example's identity rotations only")

    transform = _object(candidate["transform"], "candidate.transform")
    dimension_groups = _object(transform["dimension_groups"], "candidate.transform.dimension_groups")
    if not dimension_groups:
        raise ProfileGenerationError("candidate has no dimension groups")
    normalized_groups: dict[str, dict[str, Any]] = {}
    for name, raw_selector in dimension_groups.items():
        selector = _object(raw_selector, f"candidate.transform.dimension_groups.{name}")
        patterns = [_owner_pattern(item, f"candidate.transform.dimension_groups.{name}.owner_patterns[{pattern_index}]") for pattern_index, item in enumerate(_list(selector.get("owner_patterns"), f"candidate.transform.dimension_groups.{name}.owner_patterns"))]
        if not patterns:
            raise ProfileGenerationError(f"dimension group {name} has no owner patterns")
        selector["owner_patterns"] = patterns
        if ("role" in selector) == ("role_prefix" in selector):
            raise ProfileGenerationError(f"dimension group {name} must have exactly one role or role_prefix selector")
        if "role" in selector:
            selector["role"] = _text(selector["role"], f"dimension group {name}.role")
        else:
            selector["role_prefix"] = _text(selector["role_prefix"], f"dimension group {name}.role_prefix")
        suffixes = selector.get("role_suffixes", [])
        if not isinstance(suffixes, list) or any(not isinstance(suffix, str) or not suffix for suffix in suffixes):
            raise ProfileGenerationError(f"dimension group {name}.role_suffixes is invalid")
        selector["role_suffixes"] = suffixes
        normalized_groups[name] = selector

    group_members: dict[str, list[int]] = {name: [] for name in normalized_groups}
    for index, dimension in enumerate(dimensions):
        owner = _address(dimension["owner"], f"source.body.dimensions[{index}].owner", kind="part")
        dimension["owner"] = owner
        dimension["role"] = _text(dimension["role"], f"source.body.dimensions[{index}].role")
        _integer(dimension["value"], f"source.body.dimensions[{index}].value", minimum=1, maximum=MAX_SAFE_INTEGER)
        matches: list[str] = []
        for name, selector in normalized_groups.items():
            if _matches_dimension(dimension, selector):
                matches.append(name)
        if len(matches) != 1:
            raise ProfileGenerationError(f"dimension target {index} matches {len(matches)} groups: {matches}")
        group_members[matches[0]].append(index)
    missing_groups = sorted(name for name, members in group_members.items() if not members)
    if missing_groups:
        raise ProfileGenerationError("dimension groups have no source targets: " + ", ".join(missing_groups))
    return parts, dimensions, normalized_groups


def _validate_candidate(
    candidate: dict[str, Any],
    source: dict[str, Any],
    *,
    mode: str = DEFAULT_GENERATION_MODE,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, dict[str, Any]], list[str]]:
    expected_profile_count, expected_profile_ids = _profile_contract(mode)
    _require_keys(candidate, ("base_source", "canonicalization", "format", "profiles", "transform"), "candidate")
    if candidate["format"] != FORMAT:
        raise ProfileGenerationError(f"candidate.format must be {FORMAT}")
    base_source = _object(candidate["base_source"], "candidate.base_source")
    _require_keys(base_source, ("document", "namespace", "path", "sha256"), "candidate.base_source")
    for key in base_source:
        _text(base_source[key], f"candidate.base_source.{key}")
    if len(base_source["sha256"]) != 64 or any(character not in "0123456789abcdef" for character in base_source["sha256"]):
        raise ProfileGenerationError("candidate.base_source.sha256 is invalid")
    _object(candidate["canonicalization"], "candidate.canonicalization")
    parts, dimensions, groups = _validate_source_shape(source, candidate)
    transform = _object(candidate["transform"], "candidate.transform")
    _require_keys(transform, ("dimension_groups", "placement_targets", "preserved_controls", "reference_edges", "rotation_policy"), "candidate.transform")
    targets = [_text(item, f"candidate.transform.placement_targets[{index}]") for index, item in enumerate(_list(transform["placement_targets"], "candidate.transform.placement_targets"))]
    if len(set(targets)) != len(targets):
        raise ProfileGenerationError("candidate placement targets contain duplicates")
    actual_part_keys = {address_key(_address(part["address"], "source Part address", kind="part")) for part in parts}
    if set(targets) != actual_part_keys:
        raise ProfileGenerationError("candidate placement targets do not exactly cover source Parts")
    if transform["preserved_controls"] != PRESERVED_CONTROLS:
        raise ProfileGenerationError("candidate preserved-control declaration is not the exact enforced set")
    if not _list(transform["reference_edges"], "candidate.transform.reference_edges"):
        raise ProfileGenerationError("candidate declares no stable reference edge")
    profiles = _list(candidate["profiles"], "candidate.profiles")
    if len(profiles) != expected_profile_count:
        raise ProfileGenerationError(f"candidate must freeze exactly {expected_profile_count} profiles, found {len(profiles)}")
    profile_ids: list[str] = []
    profile_labels: list[str] = []
    group_names = set(groups)
    for index, raw_profile in enumerate(profiles):
        profile = _object(raw_profile, f"candidate.profiles[{index}]")
        _require_keys(profile, ("dimension_scales", "id", "label", "part_placements"), f"candidate.profiles[{index}]")
        profile_id = _text(profile["id"], f"candidate.profiles[{index}].id")
        if not IDENTIFIER.fullmatch(profile_id) or profile_id in profile_ids:
            raise ProfileGenerationError(f"candidate profile ID is not unique and restricted: {profile_id}")
        profile_ids.append(profile_id)
        label = _text(profile["label"], f"candidate.profiles[{index}].label")
        if label in profile_labels:
            raise ProfileGenerationError(f"candidate profile label is not unique: {label}")
        profile_labels.append(label)
        scales = _object(profile["dimension_scales"], f"candidate.profiles[{index}].dimension_scales")
        if set(scales) != group_names:
            raise ProfileGenerationError(f"profile {profile_id} dimension scale keys do not exactly cover groups")
        for group_name, scale in scales.items():
            _integer(scale, f"profile {profile_id}.dimension_scales.{group_name}", minimum=1, maximum=10_000)
        placements = _object(profile["part_placements"], f"candidate.profiles[{index}].part_placements")
        placement_keys = {parse_address_key(key, f"profile {profile_id}.part_placements key") for key in placements}
        if placement_keys != set(targets):
            raise ProfileGenerationError(f"profile {profile_id} placement targets do not exactly cover source Parts")
        for key, vector in placements.items():
            parsed = parse_address_key(key, f"profile {profile_id}.part_placements key")
            if parsed not in actual_part_keys or parsed.split("|")[1] != "part":
                raise ProfileGenerationError(f"profile {profile_id} has an unknown Part placement target {key}")
            _vector(vector, f"profile {profile_id}.part_placements.{key}")
    if expected_profile_ids is not None and tuple(profile_ids) != expected_profile_ids:
        if mode == DEFAULT_GENERATION_MODE:
            raise ProfileGenerationError("active mode requires the exact five-profile ID/order tuple")
        raise ProfileGenerationError("historical mode requires the exact frozen four-profile order")
    if mode == DEFAULT_GENERATION_MODE and profile_ids[0] != STANDARD_NEUTRAL_PROFILE_ID:
        raise ProfileGenerationError(
            f"the first profile must be the {STANDARD_NEUTRAL_PROFILE_ID} neutral reference"
        )
    if mode == DEFAULT_GENERATION_MODE:
        neutral = profiles[0]
        if any(scale != 1000 for scale in neutral["dimension_scales"].values()):
            raise ProfileGenerationError("the standard neutral reference must use 1000-permille dimension scales")
        source_placements = {
            address_key(part["address"]): tuple(part["placement"]["translation"])
            for part in parts
        }
        for key, vector in neutral["part_placements"].items():
            if tuple(vector) != source_placements[key]:
                raise ProfileGenerationError(
                    "the standard neutral reference must retain the base source Part placements"
                )
    return parts, dimensions, groups, profile_ids


def _transform_signature(profile: dict[str, Any]) -> tuple[tuple[tuple[str, tuple[int, int, int]], ...], tuple[tuple[str, int], ...]]:
    placements = tuple(
        sorted(
            (parse_address_key(key, f"profile {profile['id']}.part_placements key"), tuple(_vector(vector, f"profile {profile['id']}.part_placements.{key}")))
            for key, vector in profile["part_placements"].items()
        )
    )
    scales = tuple(sorted((name, _integer(scale, f"profile {profile['id']}.dimension_scales.{name}", minimum=1, maximum=10_000)) for name, scale in profile["dimension_scales"].items()))
    return placements, scales


def _preserved_snapshot(source: dict[str, Any]) -> dict[str, Any]:
    body = source["body"]
    return {
        "landmarks": copy.deepcopy(body["landmarks"]),
        "frames": copy.deepcopy(body["frames"]),
        "joints": copy.deepcopy(body["joints"]),
        "sockets": copy.deepcopy(body["sockets"]),
        "attachments": copy.deepcopy(body["attachments"]),
    }


def _assert_preserved(source: dict[str, Any], candidate: dict[str, Any], snapshot: dict[str, Any]) -> None:
    body = candidate["body"]
    if body["landmarks"] != snapshot["landmarks"] or body["frames"] != snapshot["frames"]:
        raise ProfileGenerationError("normalized route controls were modified")
    if body["joints"] != snapshot["joints"]:
        raise ProfileGenerationError("Joint records were modified")
    if body["sockets"] != snapshot["sockets"]:
        raise ProfileGenerationError("Socket records were modified")
    if body["attachments"] != snapshot["attachments"]:
        raise ProfileGenerationError("Attachment records were modified")
    source_rotations = _rotation_paths(source)
    candidate_rotations = _rotation_paths(candidate)
    if source_rotations != candidate_rotations:
        raise ProfileGenerationError("a source rotation changed")


def _reference_edge_check(source: dict[str, Any], generated: dict[str, Any], transform: dict[str, Any]) -> None:
    edges = _list(transform["reference_edges"], "candidate.transform.reference_edges")
    candidate_world = _world_part_translations(source)
    output_world = _world_part_translations(generated)
    for index, raw_edge in enumerate(edges):
        edge = _object(raw_edge, f"candidate.transform.reference_edges[{index}]")
        _require_keys(edge, ("child", "expected_translation", "parent", "squared_length"), f"candidate.transform.reference_edges[{index}]")
        child = parse_address_key(edge["child"], f"candidate.transform.reference_edges[{index}].child")
        parent = parse_address_key(edge["parent"], f"candidate.transform.reference_edges[{index}].parent")
        expected = _vector(edge["expected_translation"], f"candidate.transform.reference_edges[{index}].expected_translation")
        squared_length = _integer(edge["squared_length"], f"candidate.transform.reference_edges[{index}].squared_length", minimum=1)
        for world, label in ((candidate_world, "source"), (output_world, "generated source")):
            if child not in world or parent not in world:
                raise ProfileGenerationError(f"{label} reference edge names an unknown Part")
            delta = tuple(world[child][axis] - world[parent][axis] for axis in range(3))
            if delta != tuple(expected):
                raise ProfileGenerationError(f"{label} reference edge translation is not stable")
        if sum(value * value for value in expected) != squared_length:
            raise ProfileGenerationError("reference edge squared length is not exact")


def tail_signature(source: dict[str, Any]) -> tuple[int, int, int, int, int]:
    """Return the deterministic source-owned tail shape signature."""
    body = source["body"]
    tips = [item for item in body["parts"] if item["address"]["role"] == "tail_tip" and item["address"]["anchors"] == ["tail"]]
    if len(tips) != 1:
        raise ProfileGenerationError("generated source must contain exactly one tail_tip Part")
    tip = tips[0]
    tip_translation = tuple(tip["placement"]["translation"])
    dimensions = {(tuple(item["owner"]["anchors"]), item["owner"]["role"], item["role"]): item["value"] for item in body["dimensions"]}
    keys = [
        (("tail",), "tail_root", "form_start_radius"),
        (("tail",), "tail_root", "form_end_radius"),
        (("tail",), "tail_tip", "form_start_radius"),
        (("tail",), "tail_tip", "form_end_radius"),
    ]
    if any(key not in dimensions for key in keys):
        raise ProfileGenerationError("generated source is missing a tail taper dimension")
    return (abs(tip_translation[2]), *(dimensions[key] for key in keys))


# Keep the historical private name available to existing experiment consumers.
_tail_signature = tail_signature


def _check_shared_pose_alignment(source: dict[str, Any], where: str) -> None:
    """Retain the candidate's mirrored, axis-aligned neutral source posture."""

    world = _world_part_translations(source)
    namespace = _text(source["source"]["namespace"], f"{where}.source.namespace")

    def point(role: str, anchors: tuple[str, ...] = ()) -> tuple[int, int, int]:
        key = f"{namespace}|part|{','.join(anchors)}|{role}"
        if key not in world:
            raise ProfileGenerationError(f"{where} is missing neutral-pose Part {key}")
        return world[key]

    for role in ("upper_arm", "forearm", "hand", "thigh", "shin", "foot"):
        left = point(role, ("left",))
        right = point(role, ("right",))
        if right != (-left[0], left[1], left[2]):
            raise ProfileGenerationError(f"{where} breaks bilateral neutral-pose symmetry for {role}")
    neck_height = point("neck")[1]
    if any(point("upper_arm", (side,))[1] != neck_height for side in ("left", "right")):
        raise ProfileGenerationError(f"{where} does not align shoulder roots with the neck-base level")
    if any(point(role)[0] != 0 for role in ("pelvis", "torso", "neck", "head")):
        raise ProfileGenerationError(f"{where} moves an axial core Part off the shared centerline")


def _apply_profile(source: dict[str, Any], profile: dict[str, Any], groups: dict[str, dict[str, Any]]) -> dict[str, Any]:
    output = copy.deepcopy(source)
    profile_id = profile["id"]
    output["source"]["document"] = f"{source['source']['document']}__{SOURCE_DOCUMENT_SUFFIX}__{profile_id}"
    for module in output["body"]["modules"]:
        module["declaration"]["document"] = output["source"]["document"]
    placements = profile["part_placements"]
    for part in output["body"]["parts"]:
        key = address_key(part["address"])
        if key not in placements:
            raise ProfileGenerationError(f"profile {profile_id} is missing transform target {key}")
        expected = _vector(placements[key], f"profile {profile_id}.part_placements.{key}")
        part["placement"]["translation"] = expected
    if set(placements) != {address_key(part["address"]) for part in output["body"]["parts"]}:
        raise ProfileGenerationError(f"profile {profile_id} has an unknown transform target")

    for index, dimension in enumerate(output["body"]["dimensions"]):
        matches = [name for name, selector in groups.items() if _matches_dimension(dimension, selector)]
        if len(matches) != 1:
            raise ProfileGenerationError(f"profile {profile_id} dimension {index} lost its transform target")
        scale = profile["dimension_scales"].get(matches[0])
        if scale is None:
            raise ProfileGenerationError(f"profile {profile_id} is missing transform target group {matches[0]}")
        value = _integer(dimension["value"], f"source.body.dimensions[{index}].value", minimum=1)
        scaled = _round_permille(value, _integer(scale, f"profile {profile_id}.dimension_scales.{matches[0]}", minimum=1, maximum=10_000))
        if scaled < 1 or scaled > MAX_SAFE_INTEGER:
            raise ProfileGenerationError(f"profile {profile_id} generated an unsafe permille value")
        dimension["value"] = scaled
    return output


def _generate_sources(
    candidate: dict[str, Any],
    source: dict[str, Any],
    *,
    mode: str = DEFAULT_GENERATION_MODE,
) -> list[dict[str, Any]]:
    candidate = copy.deepcopy(candidate)
    source = copy.deepcopy(source)
    expected_profile_count, expected_profile_ids = _profile_contract(mode)
    if mode == HISTORICAL_GENERATION_MODE:
        _, historical_candidate_bytes, historical_source, _ = _historical_fixture_values()
        if canonical_bytes(candidate) != historical_candidate_bytes:
            raise ProfileGenerationError("historical mode requires the archived candidate-table bytes")
        if canonical_source_bytes(source) != canonical_source_bytes(historical_source):
            raise ProfileGenerationError("historical mode requires the archived source semantics")
    parts, dimensions, groups, profile_ids = _validate_candidate(candidate, source, mode=mode)
    del parts, dimensions
    signatures = [_transform_signature(profile) for profile in candidate["profiles"]]
    if len(set(signatures)) != len(signatures):
        raise ProfileGenerationError("profile transforms must be pairwise semantically distinct")
    source_snapshot = _preserved_snapshot(source)
    outputs: list[dict[str, Any]] = []
    tail_signatures: set[tuple[int, int, int, int, int]] = set()
    for profile in candidate["profiles"]:
        output = _apply_profile(source, profile, groups)
        _assert_preserved(source, output, source_snapshot)
        _reference_edge_check(source, output, _object(candidate["transform"], "candidate.transform"))
        _check_attachment_equations(output, f"profile {profile['id']}")
        _check_shared_pose_alignment(output, f"profile {profile['id']}")
        tail_modules = [module for module in output["body"]["modules"] if module["module"] == "tail"]
        if len(tail_modules) != 1 or tail_modules[0]["presence"] != "present" or tail_modules[0]["root"] is None:
            raise ProfileGenerationError(f"profile {profile['id']} does not retain a present tail module")
        tail_signatures.add(tail_signature(output))
        outputs.append(output)
    if len(tail_signatures) < 2:
        raise ProfileGenerationError(f"the {expected_profile_count} present tails do not provide style contrast")
    if expected_profile_ids is not None and tuple(profile_ids) != expected_profile_ids:
        raise ProfileGenerationError("generated historical source lineage is not deterministic")
    if len(outputs) != expected_profile_count or [output["source"]["document"] for output in outputs] != [f"{source['source']['document']}__{SOURCE_DOCUMENT_SUFFIX}__{profile_id}" for profile_id in profile_ids]:
        raise ProfileGenerationError("generated source lineage is not deterministic")
    return outputs


def generate_sources(
    candidate: dict[str, Any],
    source: dict[str, Any],
    *,
    mode: str = DEFAULT_GENERATION_MODE,
) -> list[dict[str, Any]]:
    try:
        return _generate_sources(candidate, source, mode=mode)
    except ProfileGenerationError:
        raise
    except (AttributeError, IndexError, KeyError, OverflowError, RecursionError, TypeError, ValueError) as exc:
        raise ProfileGenerationError("candidate or source contains malformed validated structure") from exc


def write_sources(
    candidate_path: Path,
    source_path: Path,
    output_dir: Path,
    *,
    mode: str = DEFAULT_GENERATION_MODE,
) -> dict[str, Any]:
    _profile_contract(mode)
    candidate_path = _path_without_symlinks(candidate_path, "candidate path")
    source_path = _path_without_symlinks(source_path, "authored source path")
    output_dir = _path_without_symlinks(output_dir, "output path")
    output_parent = _path_without_symlinks(output_dir.parent, "output parent path")
    try:
        output_parent_info = output_parent.lstat()
    except FileNotFoundError as exc:
        raise ProfileGenerationError(f"output parent must already exist: {output_parent}") from exc
    except OSError as exc:
        raise ProfileGenerationError(f"could not inspect output parent: {output_parent}") from exc
    if not stat.S_ISDIR(output_parent_info.st_mode):
        raise ProfileGenerationError(f"output parent is not an existing directory: {output_parent}")
    output_parent_identity = (output_parent_info.st_dev, output_parent_info.st_ino)
    candidate, candidate_bytes = load_json_with_bytes(candidate_path, "candidate")
    source, source_bytes = load_json_with_bytes(source_path, "authored source")
    candidate_object = _object(candidate, "candidate")
    _object(source, "authored source")
    base_source = _object(candidate_object.get("base_source"), "candidate.base_source")
    expected_source_hash = _text(base_source.get("sha256"), "candidate.base_source.sha256")
    if hashlib.sha256(source_bytes).hexdigest() != expected_source_hash:
        raise ProfileGenerationError("authored source bytes do not match candidate.base_source.sha256")
    if mode == HISTORICAL_GENERATION_MODE:
        _, expected_candidate_bytes, _, expected_source_bytes = _historical_fixture_values()
        if candidate_bytes != expected_candidate_bytes:
            raise ProfileGenerationError("historical mode requires the archived candidate-table bytes")
        if source_bytes != expected_source_bytes:
            raise ProfileGenerationError("historical mode requires the archived source bytes")
    outputs = generate_sources(candidate, source, mode=mode)
    try:
        output_dir.lstat()
    except FileNotFoundError:
        pass
    except OSError as exc:
        raise ProfileGenerationError(f"could not inspect output directory: {output_dir}") from exc
    else:
        raise ProfileGenerationError(f"output directory already exists: {output_dir}")
    parent_fd = None
    stage_name = None
    try:
        parent_fd = structural_atomic_publish.open_directory_no_symlinks(
            output_parent,
            output_parent_identity,
        )
        stage_name, stage = structural_atomic_publish.create_stage(parent_fd, output_dir.name)
    except (OSError, structural_atomic_publish.AtomicPublishError) as exc:
        if parent_fd is not None:
            os.close(parent_fd)
        raise ProfileGenerationError(f"could not create secure output staging: {exc}") from exc
    records: list[dict[str, Any]] = []
    try:
        for profile, output in zip(candidate["profiles"], outputs):
            file_name = f"{profile['id']}.json"
            data = canonical_source_bytes(output)
            if len(data) > MAX_OUTPUT_JSON_BYTES:
                raise ProfileGenerationError(f"generated source exceeds the bounded JSON size: {file_name}")
            (stage / file_name).write_bytes(data)
            records.append({
                "bytes": len(data),
                "document": output["source"]["document"],
                "file": file_name,
                "id": profile["id"],
                "sha256": hashlib.sha256(data).hexdigest(),
                "tail_signature": list(tail_signature(output)),
            })
        manifest = {
            "candidate_format": candidate["format"],
            "format": "creature-kernel.disposable-structural-profile-source-manifest.v1",
            "profiles": records,
            "source": {
                "base_document": source["source"]["document"],
                "base_namespace": source["source"]["namespace"],
                "candidate_sha256": hashlib.sha256(candidate_bytes).hexdigest(),
                "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
            },
        }
        manifest_bytes = canonical_bytes(manifest)
        if len(manifest_bytes) > MAX_OUTPUT_JSON_BYTES:
            raise ProfileGenerationError("generated manifest exceeds the bounded JSON size")
        (stage / "manifest.json").write_bytes(manifest_bytes)
        _atomic_publish_no_replace(parent_fd, stage_name, output_dir.name)
        return manifest
    except Exception:
        structural_atomic_publish.cleanup_stage(parent_fd, stage_name)
        raise
    finally:
        structural_atomic_publish.close_stage(stage_name)
        os.close(parent_fd)


def _atomic_publish_no_replace(parent_fd: int, stage_name: str, destination_name: str) -> None:
    try:
        structural_atomic_publish.publish_no_replace(parent_fd, stage_name, destination_name)
    except FileExistsError as exc:
        raise ProfileGenerationError(f"output directory already exists: {destination_name}") from exc
    except structural_atomic_publish.AtomicPublishError as exc:
        raise ProfileGenerationError(str(exc)) from exc


def _default_source(candidate_path: Path) -> Path:
    candidate_path = _path_without_symlinks(candidate_path, "candidate path")
    candidate = load_json(candidate_path, "candidate")
    candidate_object = _object(candidate, "candidate")
    base_source = _object(candidate_object.get("base_source"), "candidate.base_source")
    raw = _text(base_source.get("path"), "candidate.base_source.path")
    if "\\" in raw or "\x00" in raw:
        raise ProfileGenerationError("candidate.base_source.path is not a safe repository-relative path")
    relative = PurePosixPath(raw)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise ProfileGenerationError("candidate.base_source.path is not a safe repository-relative path")
    return _path_without_symlinks(REPO_ROOT.joinpath(*relative.parts), "default source path")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument(
        "--generation-mode",
        choices=(DEFAULT_GENERATION_MODE, HISTORICAL_GENERATION_MODE),
        default=DEFAULT_GENERATION_MODE,
        help="select the explicit active or archived historical source contract",
    )
    parser.add_argument("--check", action="store_true", help="validate and generate in a temporary directory without retaining output")
    args = parser.parse_args(argv)
    if not args.check and args.output_dir is None:
        parser.error("--output-dir is required unless --check is used")
    try:
        candidate_path = args.candidate or (
            HISTORICAL_CANDIDATE if args.generation_mode == HISTORICAL_GENERATION_MODE else DEFAULT_CANDIDATE
        )
        source_path = args.source or (
            HISTORICAL_SOURCE
            if args.generation_mode == HISTORICAL_GENERATION_MODE
            else _default_source(candidate_path)
        )
        if args.check:
            with tempfile.TemporaryDirectory(prefix="ck-structural-profile-check-") as temporary:
                manifest = write_sources(
                    candidate_path,
                    source_path,
                    Path(temporary) / "sources",
                    mode=args.generation_mode,
                )
        else:
            manifest = write_sources(
                candidate_path,
                source_path,
                args.output_dir,
                mode=args.generation_mode,
            )
    except ProfileGenerationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"generated {len(manifest['profiles'])} structural profile sources")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

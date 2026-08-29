#!/usr/bin/env python3
"""Build and validate an experiment-local semantic-contact command."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

EXPERIMENT_ROOT = Path(__file__).resolve().parent
CARRIER_MODULE_PATH = EXPERIMENT_ROOT / "disposable_avatar_carrier.py"
POSE_COMMAND_MODULE_PATH = EXPERIMENT_ROOT / "disposable_semantic_pose_command.py"

SCHEMA = "creature-kernel.disposable-semantic-contact-command.v1"
BOUNDARY = "experiment_local_contact_command_evidence_only_no_adapter_or_runtime_conformance"
COMMAND_ID = "probe-single-semantic-contact"
COMMAND_VERSION = 1
MAPPING_REVISION = "joint-selector-to-posed-proxy-v1"
POSE_SCHEMA = "creature-kernel.disposable-semantic-pose-command.v1"
POSE_BOUNDARY = "experiment_local_command_evidence_only_no_adapter_or_runtime_conformance"
POSE_COMMAND_ID = "inject-semantic-pose"
POSE_COMMAND_VERSION = 1
MAX_COMMAND_BYTES = 64 * 1024
MAX_IDENTIFIER_BYTES = 256
HASH_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
DECIMAL_PATTERN = re.compile(r"(?:0|[1-9][0-9]*)\Z")
WINDOWS_DRIVE_PREFIX_PATTERN = re.compile(r"[A-Za-z]:")

COMMAND_KEYS = (
    "schema",
    "boundary",
    "command_id",
    "command_version",
    "mapping_revision",
    "targets",
    "source_pose_command",
    "participants",
    "interaction",
)
TARGET_KEYS = ("instance_id", "profile_id", "candidate_profile_sha256")
POSE_IDENTITY_KEYS = (
    "sha256",
    "byte_count_decimal",
    "schema",
    "boundary",
    "command_id",
    "command_version",
)
PARTICIPANT_KEYS = ("role", "target_index", "selector")
SELECTOR_KEYS = ("kind", "role", "anchors")
INTERACTION_KEYS = ("kind", "phase_order")
EXPECTED_PARTICIPANTS = [
    {"role": "actuator", "target_index": 0, "selector": {"kind": "joint", "role": "wrist", "anchors": ["right"]}},
    {"role": "response", "target_index": 1, "selector": {"kind": "joint", "role": "wrist", "anchors": ["left"]}},
]
EXPECTED_INTERACTION = {
    "kind": "single-proxy-press-release",
    "phase_order": ["approach", "contact", "release", "exit"],
}

FORBIDDEN_FIELD_NAMES = {
    "adapter",
    "body_type",
    "deformation",
    "distance",
    "godot",
    "host",
    "mass",
    "masses",
    "node",
    "node_name",
    "package",
    "performance",
    "r3",
    "readiness",
    "solver",
    "ticks",
}


class CommandError(ValueError):
    """A bounded, fail-closed contact-command validation or publication error."""


ContactCommandError = CommandError


_CARRIER_MODULE: Any | None = None
_POSE_COMMAND_MODULE: Any | None = None


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _load_carrier_module() -> Any:
    global _CARRIER_MODULE
    if _CARRIER_MODULE is not None:
        return _CARRIER_MODULE
    try:
        # Loading the carrier by file path does not otherwise put its direct
        # structural-gallery import on sys.path when this module is imported
        # by a test harness rather than executed as a script.
        if "run_structural_gallery_smoke" not in sys.modules:
            _load_module(
                "neutral_structural_gallery_smoke_for_semantic_contact_command",
                EXPERIMENT_ROOT / "run_structural_gallery_smoke.py",
            )
            sys.modules["run_structural_gallery_smoke"] = sys.modules[
                "neutral_structural_gallery_smoke_for_semantic_contact_command"
            ]
        # The pose module loads the same structural-gallery/carrier predecessor
        # infrastructure; keep this command's imports isolated and disposable.
        _CARRIER_MODULE = _load_module(
            "disposable_avatar_carrier_for_semantic_contact_command",
            CARRIER_MODULE_PATH,
        )
    except Exception as exc:
        raise ContactCommandError(f"could not load the existing carrier infrastructure: {exc}") from exc
    return _CARRIER_MODULE


def _load_pose_command_module() -> Any:
    global _POSE_COMMAND_MODULE
    if _POSE_COMMAND_MODULE is not None:
        return _POSE_COMMAND_MODULE
    try:
        _POSE_COMMAND_MODULE = _load_module(
            "disposable_semantic_pose_command_for_semantic_contact_command",
            POSE_COMMAND_MODULE_PATH,
        )
    except Exception as exc:
        raise ContactCommandError(f"could not load the existing semantic pose command: {exc}") from exc
    return _POSE_COMMAND_MODULE


def _canonical_json(value: Any) -> bytes:
    try:
        return (
            json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise ContactCommandError("semantic contact command cannot be encoded as canonical finite JSON") from exc


def _exact_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return set(left) == set(right) and all(_exact_equal(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(_exact_equal(a, b) for a, b in zip(left, right))
    return left == right


def _bounded_string(value: Any, where: str, *, allow_empty: bool = False) -> str:
    if type(value) is not str or (not allow_empty and not value):
        raise ContactCommandError(f"{where} must be a bounded string")
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ContactCommandError(f"{where} must be valid UTF-8") from exc
    if len(encoded) > MAX_IDENTIFIER_BYTES:
        raise ContactCommandError(f"{where} exceeds {MAX_IDENTIFIER_BYTES} UTF-8 bytes")
    return value


def _hash(value: Any, where: str) -> None:
    if type(value) is not str or HASH_PATTERN.fullmatch(value) is None:
        raise ContactCommandError(f"{where} must be a lowercase SHA-256 string")


def _reject_unsafe_serialized_data(value: Any, where: str = "semantic contact command") -> None:
    """Reject forbidden field names and path-shaped serialized strings.

    String values are not vocabulary-scanned: ordinary identifiers may contain
    words such as ``host`` or ``adapter``. Exact shape and lineage validation
    own those value semantics.
    """
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ContactCommandError(f"{where} contains a non-string field name")
            if key.casefold() in FORBIDDEN_FIELD_NAMES or any(token in key.casefold() for token in ("adapter", "package", "readiness", "host", "godot")):
                raise ContactCommandError(f"{where}.{key} is forbidden in experiment-only contact data")
            _reject_unsafe_serialized_data(item, f"{where}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_unsafe_serialized_data(item, f"{where}[{index}]")
    elif isinstance(value, str):
        if "/" in value or "\\" in value or WINDOWS_DRIVE_PREFIX_PATTERN.match(value):
            raise ContactCommandError(f"{where} must not contain a path")


def _validate_pose_identity(value: Any) -> None:
    if not isinstance(value, dict) or set(value) != set(POSE_IDENTITY_KEYS):
        raise ContactCommandError("semantic contact command source pose identity is incomplete or has extra fields")
    _hash(value["sha256"], "semantic contact command source pose identity SHA-256")
    byte_count = value["byte_count_decimal"]
    _bounded_string(byte_count, "semantic contact command source pose identity byte count")
    if DECIMAL_PATTERN.fullmatch(byte_count) is None:
        raise ContactCommandError("semantic contact command source pose identity byte count is not canonical decimal")
    if value["schema"] != POSE_SCHEMA:
        raise ContactCommandError("semantic contact command source pose identity schema is invalid")
    if value["boundary"] != POSE_BOUNDARY:
        raise ContactCommandError("semantic contact command source pose identity boundary is invalid")
    if value["command_id"] != POSE_COMMAND_ID:
        raise ContactCommandError("semantic contact command source pose identity command ID is invalid")
    if type(value["command_version"]) is not int or value["command_version"] != POSE_COMMAND_VERSION:
        raise ContactCommandError("semantic contact command source pose identity version is invalid")


def _validate_targets(value: Any) -> None:
    if not isinstance(value, list) or len(value) != 2:
        raise ContactCommandError("semantic contact command must contain exactly two ordered targets")
    carrier = _load_carrier_module()
    seen: set[str] = set()
    for index, target in enumerate(value):
        if not isinstance(target, dict) or set(target) != set(TARGET_KEYS):
            raise ContactCommandError(f"semantic contact command target {index} has unexpected or missing fields")
        instance_id = target["instance_id"]
        if type(instance_id) is not str or carrier.INSTANCE_ID_PATTERN.fullmatch(instance_id) is None:
            raise ContactCommandError(f"semantic contact command target {index}.instance_id is unsafe")
        if instance_id in seen:
            raise ContactCommandError("semantic contact command target instance IDs are not unique")
        seen.add(instance_id)
        _bounded_string(target["profile_id"], f"semantic contact command target {index}.profile_id")
        _hash(target["candidate_profile_sha256"], f"semantic contact command target {index}.candidate_profile_sha256")


def _validate_participants(value: Any) -> None:
    if not _exact_equal(value, EXPECTED_PARTICIPANTS):
        raise ContactCommandError("semantic contact command participants must be the exact actuator/response pair")
    for index, participant in enumerate(value):
        if set(participant) != set(PARTICIPANT_KEYS) or set(participant["selector"]) != set(SELECTOR_KEYS):
            raise ContactCommandError(f"semantic contact command participant {index} has unexpected fields")
        if type(participant["target_index"]) is not int:
            raise ContactCommandError(f"semantic contact command participant {index}.target_index is invalid")


def _validate_interaction(value: Any) -> None:
    if not _exact_equal(value, EXPECTED_INTERACTION):
        raise ContactCommandError("semantic contact command interaction must be the exact press-release phase order")
    if set(value) != set(INTERACTION_KEYS):
        raise ContactCommandError("semantic contact command interaction has unexpected fields")


def _validate_shape(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContactCommandError("semantic contact command must be a JSON object")
    _reject_unsafe_serialized_data(value)
    if set(value) != set(COMMAND_KEYS):
        raise ContactCommandError("semantic contact command has unexpected or missing top-level fields")
    if value["schema"] != SCHEMA or value["boundary"] != BOUNDARY:
        raise ContactCommandError("semantic contact command schema or boundary is invalid")
    if type(value["command_id"]) is not str or value["command_id"] != COMMAND_ID:
        raise ContactCommandError("semantic contact command identity is invalid")
    if type(value["command_version"]) is not int or value["command_version"] != COMMAND_VERSION:
        raise ContactCommandError("semantic contact command version is invalid")
    if value["mapping_revision"] != MAPPING_REVISION:
        raise ContactCommandError("semantic contact command mapping revision is invalid")
    _validate_targets(value["targets"])
    _validate_pose_identity(value["source_pose_command"])
    _validate_participants(value["participants"])
    _validate_interaction(value["interaction"])
    carrier = _load_carrier_module()
    try:
        carrier._finite_json(value, "semantic contact command")
    except Exception as exc:
        raise ContactCommandError(f"semantic contact command exceeds bounded JSON limits: {exc}") from exc
    if len(_canonical_json(value)) > MAX_COMMAND_BYTES:
        raise ContactCommandError(f"semantic contact command exceeds the bounded size of {MAX_COMMAND_BYTES} bytes")
    return value


def _absolute_path(path: Path, label: str) -> Path:
    path = Path(path)
    if not path.is_absolute():
        raise ContactCommandError(f"{label} must be an absolute path: {path}")
    return path


def _validated_predecessors(gallery: Path, carrier_path: Path, pose_command_path: Path) -> dict[str, Any]:
    gallery = _absolute_path(gallery, "gallery path")
    carrier_path = _absolute_path(carrier_path, "carrier path")
    pose_command_path = _absolute_path(pose_command_path, "semantic pose command path")
    carrier_module = _load_carrier_module()
    pose_module = _load_pose_command_module()
    try:
        carrier_value = carrier_module.load_carrier(carrier_path)
        carrier_payload, profile_ids, instance_ids = carrier_module.validate_carrier(carrier_value, gallery)
        carrier_bytes = carrier_module._read_carrier_bytes(carrier_path)
        if carrier_bytes != carrier_module._canonical_json(carrier_value):
            raise ContactCommandError("carrier changed while its exact identity was being read")
        pose_value = pose_module.load_command(pose_command_path)
        pose_module.validate_command(pose_value, gallery, carrier_path)
        pose_identity = pose_module.command_identity(pose_value)
        pose_bytes = carrier_module._read_regular_file(
            pose_command_path,
            pose_module.MAX_COMMAND_BYTES,
            "semantic pose command",
        )
        if pose_bytes != pose_module._canonical_json(pose_value):
            raise ContactCommandError("semantic pose command changed while its exact identity was being read")
    except ContactCommandError:
        raise
    except Exception as exc:
        raise ContactCommandError(f"carrier and semantic pose predecessors were rejected: {exc}") from exc
    if not isinstance(carrier_value, dict) or not isinstance(carrier_payload, dict):
        raise ContactCommandError("carrier predecessor validation did not return object values")
    if len(profile_ids) != 2 or len(instance_ids) != 2:
        raise ContactCommandError("carrier predecessor validation did not return exactly two ordered identities")
    return {
        "carrier": carrier_value,
        "carrier_bytes": carrier_bytes,
        "payload": carrier_payload,
        "profile_ids": tuple(profile_ids),
        "instance_ids": tuple(instance_ids),
        "pose": pose_value,
        "pose_bytes": pose_bytes,
        "pose_identity": pose_identity,
    }


def _assert_predecessors_unchanged(initial: dict[str, Any], final: dict[str, Any]) -> None:
    for key in ("carrier", "carrier_bytes", "payload", "profile_ids", "instance_ids", "pose", "pose_bytes", "pose_identity"):
        if not _exact_equal(initial[key], final[key]):
            raise ContactCommandError(f"predecessor {key} changed during contact-command construction")


def build_contact_command(gallery: Path, carrier_path: Path, pose_command_path: Path) -> dict[str, Any]:
    """Build a fixed semantic-contact command from freshly validated predecessors."""
    initial = _validated_predecessors(gallery, carrier_path, pose_command_path)
    targets = [
        {
            "instance_id": instance["instance_id"],
            "profile_id": instance["profile_id"],
            "candidate_profile_sha256": instance["candidate_profile_sha256"],
        }
        for instance in initial["carrier"]["instances"]
    ]
    command = {
        "schema": SCHEMA,
        "boundary": BOUNDARY,
        "command_id": COMMAND_ID,
        "command_version": COMMAND_VERSION,
        "mapping_revision": MAPPING_REVISION,
        "targets": targets,
        "source_pose_command": initial["pose_identity"],
        "participants": json.loads(json.dumps(EXPECTED_PARTICIPANTS)),
        "interaction": json.loads(json.dumps(EXPECTED_INTERACTION)),
    }
    _validate_shape(command)
    _assert_predecessors_unchanged(initial, _validated_predecessors(gallery, carrier_path, pose_command_path))
    return command


def load_contact_command(path: Path) -> dict[str, Any]:
    """Load one canonical contact command and validate its local shape."""
    carrier = _load_carrier_module()
    try:
        data = carrier._read_regular_file(
            Path(path),
            MAX_COMMAND_BYTES,
            "semantic contact command",
            size_error=f"semantic contact command exceeds the bounded input size of {MAX_COMMAND_BYTES} bytes",
        )
    except Exception as exc:
        raise ContactCommandError(f"semantic contact command could not be read: {exc}") from exc
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=carrier._unique_object,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
        carrier._finite_json(value, "semantic contact command")
    except Exception as exc:
        raise ContactCommandError(f"semantic contact command is not valid finite UTF-8 JSON: {path}") from exc
    if data != _canonical_json(value):
        raise ContactCommandError("semantic contact command is not canonical newline-terminated JSON")
    return _validate_shape(value)


def validate_contact_command(value: Any, gallery: Path, carrier_path: Path, pose_command_path: Path) -> dict[str, Any]:
    """Rebuild and compare a contact command against fresh predecessor lineage."""
    _validate_shape(value)
    expected = build_contact_command(gallery, carrier_path, pose_command_path)
    if not _exact_equal(value, expected):
        raise ContactCommandError("semantic contact command does not exactly match the validated predecessors")
    return value


def command_identity(value: dict[str, Any]) -> dict[str, Any]:
    """Return the canonical transport identity of a validated contact command."""
    _validate_shape(value)
    canonical = _canonical_json(value)
    return {
        "sha256": hashlib.sha256(canonical).hexdigest(),
        "byte_count_decimal": str(len(canonical)),
        "schema": value["schema"],
        "boundary": value["boundary"],
        "command_id": value["command_id"],
        "command_version": value["command_version"],
    }


def write_contact_command(path: Path, value: dict[str, Any]) -> None:
    """Publish canonical command bytes through the existing no-overwrite writer."""
    _validate_shape(value)
    canonical = _canonical_json(value)
    if len(canonical) > MAX_COMMAND_BYTES:
        raise ContactCommandError(f"semantic contact command exceeds the bounded size of {MAX_COMMAND_BYTES} bytes")
    try:
        _load_carrier_module().write_carrier(path, value)
    except Exception as exc:
        raise ContactCommandError(f"semantic contact command could not be published: {exc}") from exc


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="operation", required=True)
    build = subparsers.add_parser("build", help="build and atomically publish a contact command")
    build.add_argument("--gallery", required=True, type=Path)
    build.add_argument("--carrier", required=True, type=Path)
    build.add_argument("--pose-command", "--pose", required=True, dest="pose_command", type=Path)
    build.add_argument("--output", required=True, type=Path)
    validate = subparsers.add_parser("validate", help="validate one contact command against its predecessors")
    validate.add_argument("--gallery", required=True, type=Path)
    validate.add_argument("--carrier", required=True, type=Path)
    validate.add_argument("--pose-command", "--pose", required=True, dest="pose_command", type=Path)
    validate.add_argument("--command", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        if args.operation == "build":
            value = build_contact_command(args.gallery, args.carrier, args.pose_command)
            write_contact_command(args.output, value)
        else:
            value = load_contact_command(args.command)
            validate_contact_command(value, args.gallery, args.carrier, args.pose_command)
    except (ContactCommandError, ValueError, OSError, TypeError) as exc:
        print(f"disposable semantic contact command failed: {exc}", file=sys.stderr)
        return 2
    print(_canonical_json(value).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build and validate an experiment-local semantic-pose injection command."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

EXPERIMENT_ROOT = Path(__file__).resolve().parent
CARRIER_MODULE_PATH = EXPERIMENT_ROOT / "disposable_avatar_carrier.py"
POSE_FILE = "structural_embodiment_shared_pose.json"
POSE_FORMAT = "creature-kernel.disposable-structural-embodiment-shared-pose.v1"
POSE_VERSION = 1
SCHEMA = "creature-kernel.disposable-semantic-pose-command.v1"
BOUNDARY = "experiment_local_command_evidence_only_no_adapter_or_runtime_conformance"
COMMAND_ID = "inject-semantic-pose"
COMMAND_VERSION = 1
RULE_COUNT = 18
MAX_COMMAND_BYTES = 256 * 1024
MAX_IDENTIFIER_BYTES = 256
MAX_ANCHORS_PER_SELECTOR = 8
POSE_QUATERNION_TOLERANCE = 1.0e-7
POSE_QUATERNION_DECIMAL_PLACES = 15
UNIT_TOLERANCE = 2.0e-14
HASH_PATTERN = re.compile(r"[0-9a-f]{64}\Z")

COMMAND_KEYS = (
    "schema",
    "boundary",
    "command_id",
    "command_version",
    "source_pose",
    "targets",
    "rules",
    "identity_frame",
)
SOURCE_POSE_KEYS = ("format", "pose_id", "sha256", "version")
TARGET_KEYS = ("instance_id", "profile_id", "candidate_profile_sha256")
RULE_KEYS = ("kind", "role", "anchors", "rotation_xyzw")
FRAME_KEYS = ("vectors", "rotation_storage", "C", "s", "evidence_only", "runtime_conformance")
IDENTITY_KEYS = (
    "sha256",
    "byte_count_decimal",
    "schema",
    "boundary",
    "command_id",
    "command_version",
)
IDENTITY_FRAME = {
    "vectors": "column",
    "rotation_storage": "xyzw",
    "C": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
    "s": 1.0,
    "evidence_only": True,
    "runtime_conformance": False,
}


class CommandError(ValueError):
    """A bounded, fail-closed command validation or publication error."""


_CARRIER_MODULE: Any | None = None


def _load_carrier_module() -> Any:
    global _CARRIER_MODULE
    if _CARRIER_MODULE is not None:
        return _CARRIER_MODULE
    try:
        neutral_spec = importlib.util.spec_from_file_location(
            "neutral_structural_gallery_smoke_for_semantic_pose_command",
            EXPERIMENT_ROOT / "run_structural_gallery_smoke.py",
        )
        if neutral_spec is None or neutral_spec.loader is None:
            raise ImportError("could not load the existing structural gallery runner")
        neutral = importlib.util.module_from_spec(neutral_spec)
        sys.modules[neutral_spec.name] = neutral
        neutral_spec.loader.exec_module(neutral)
        sys.modules.setdefault("run_structural_gallery_smoke", neutral)
        spec = importlib.util.spec_from_file_location(
            "disposable_avatar_carrier_for_semantic_pose_command",
            CARRIER_MODULE_PATH,
        )
        if spec is None or spec.loader is None:
            raise ImportError("could not load the existing disposable carrier")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    except Exception as exc:
        raise CommandError(f"could not load the existing carrier infrastructure: {exc}") from exc
    _CARRIER_MODULE = module
    return module


def _canonical_json(value: Any) -> bytes:
    try:
        return (
            json.dumps(
                value,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise CommandError("semantic pose command cannot be encoded as canonical finite JSON") from exc


def _exact_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return set(left) == set(right) and all(_exact_equal(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(_exact_equal(a, b) for a, b in zip(left, right))
    return left == right


def _finite_number(value: Any, where: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CommandError(f"{where} must be a finite number")
    try:
        finite = float(value)
    except OverflowError as exc:
        raise CommandError(f"{where} must be a finite number") from exc
    if not math.isfinite(finite):
        raise CommandError(f"{where} must be a finite number")
    return finite


def _hash(value: str, where: str) -> None:
    if type(value) is not str or HASH_PATTERN.fullmatch(value) is None:
        raise CommandError(f"{where} must be a lowercase SHA-256 string")


def _bounded_string(value: Any, where: str, *, allow_empty: bool = False) -> str:
    if type(value) is not str or (not allow_empty and not value):
        raise CommandError(f"{where} must be a bounded string")
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise CommandError(f"{where} must be valid UTF-8") from exc
    if len(encoded) > MAX_IDENTIFIER_BYTES:
        raise CommandError(f"{where} exceeds {MAX_IDENTIFIER_BYTES} UTF-8 bytes")
    return value


def _safe_id(value: Any, where: str) -> None:
    carrier = _load_carrier_module()
    if type(value) is not str or carrier.INSTANCE_ID_PATTERN.fullmatch(value) is None:
        raise CommandError(f"{where} is not a safe experiment instance ID")


def _validate_source_pose(value: Any) -> None:
    if not isinstance(value, dict) or set(value) != set(SOURCE_POSE_KEYS):
        raise CommandError("semantic pose command source-pose identity is incomplete or has extra fields")
    if type(value["format"]) is not str or value["format"] != POSE_FORMAT:
        raise CommandError("semantic pose command source-pose format is invalid")
    _bounded_string(value["pose_id"], "semantic pose command source-pose ID")
    _hash(value["sha256"], "semantic pose command source-pose SHA-256")
    if type(value["version"]) is not int or value["version"] != POSE_VERSION:
        raise CommandError("semantic pose command source-pose version is invalid")


def _selector(kind: str, role: Any, anchors: list[str]) -> tuple[str, Any, tuple[str, ...]]:
    return kind, role, tuple(anchors)


def _validate_rule(value: Any, index: int, selectors: set[tuple[str, Any, tuple[str, ...]]]) -> None:
    where = f"semantic pose command rule {index}"
    if not isinstance(value, dict) or set(value) != set(RULE_KEYS):
        raise CommandError(f"{where} has unexpected or missing fields")
    _bounded_string(value["kind"], f"{where}.kind")
    role = value["role"]
    if role is not None:
        _bounded_string(role, f"{where}.role", allow_empty=True)
    anchors = value["anchors"]
    if (
        not isinstance(anchors, list)
        or len(anchors) > MAX_ANCHORS_PER_SELECTOR
        or any(type(anchor) is not str for anchor in anchors)
        or len(set(anchors)) != len(anchors)
    ):
        raise CommandError(f"{where}.anchors must be an ordered list of unique strings")
    for anchor_index, anchor in enumerate(anchors):
        _bounded_string(anchor, f"{where}.anchors[{anchor_index}]", allow_empty=True)
    rotation = value["rotation_xyzw"]
    if not isinstance(rotation, list) or len(rotation) != 4:
        raise CommandError(f"{where}.rotation_xyzw must contain exactly four values")
    components = [_finite_number(item, f"{where}.rotation_xyzw[{component}]") for component, item in enumerate(rotation)]
    norm = math.sqrt(sum(component * component for component in components))
    if abs(norm - 1.0) > UNIT_TOLERANCE:
        raise CommandError(f"{where}.rotation_xyzw must be unit length")
    selector = _selector(value["kind"], role, anchors)
    if selector in selectors:
        raise CommandError("semantic pose command contains duplicate semantic selectors")
    selectors.add(selector)


def _validate_targets(value: Any) -> None:
    if not isinstance(value, list) or len(value) != 2:
        raise CommandError("semantic pose command must contain exactly two ordered targets")
    seen: set[str] = set()
    for index, target in enumerate(value):
        if not isinstance(target, dict) or set(target) != set(TARGET_KEYS):
            raise CommandError(f"semantic pose command target {index} has unexpected or missing fields")
        _safe_id(target["instance_id"], f"semantic pose command target {index}.instance_id")
        if target["instance_id"] in seen:
            raise CommandError("semantic pose command target instance IDs are not unique")
        seen.add(target["instance_id"])
        _bounded_string(target["profile_id"], f"semantic pose command target {index}.profile_id")
        _hash(target["candidate_profile_sha256"], f"semantic pose command target {index}.candidate_profile_sha256")


def _validate_frame(value: Any) -> None:
    if not isinstance(value, dict) or set(value) != set(FRAME_KEYS):
        raise CommandError("semantic pose command identity frame is incomplete or has extra fields")
    if value["vectors"] != "column" or value["rotation_storage"] != "xyzw":
        raise CommandError("semantic pose command frame must declare column vectors and xyzw rotations")
    matrix = value["C"]
    if (
        not isinstance(matrix, list)
        or len(matrix) != 3
        or any(not isinstance(row, list) or len(row) != 3 for row in matrix)
    ):
        raise CommandError("semantic pose command frame C must be a 3x3 matrix")
    for row_index, row in enumerate(matrix):
        for column_index, item in enumerate(row):
            _finite_number(item, f"semantic pose command frame C[{row_index}][{column_index}]")
    if not _exact_equal(matrix, IDENTITY_FRAME["C"]):
        raise CommandError("semantic pose command frame C must be the trial-local identity matrix")
    if type(value["s"]) is not float or value["s"] != 1.0:
        raise CommandError("semantic pose command frame s must be the exact identity scale 1.0")
    if type(value["evidence_only"]) is not bool or value["evidence_only"] is not True:
        raise CommandError("semantic pose command frame must be evidence-only")
    if type(value["runtime_conformance"]) is not bool or value["runtime_conformance"] is not False:
        raise CommandError("semantic pose command frame must not promise runtime conformance")


def _validate_shape(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != set(COMMAND_KEYS):
        raise CommandError("semantic pose command has unexpected or missing top-level fields")
    if value["schema"] != SCHEMA or value["boundary"] != BOUNDARY:
        raise CommandError("semantic pose command schema or boundary is invalid")
    if type(value["command_id"]) is not str or value["command_id"] != COMMAND_ID:
        raise CommandError("semantic pose command identity is invalid")
    if type(value["command_version"]) is not int or value["command_version"] != COMMAND_VERSION:
        raise CommandError("semantic pose command version is invalid")
    _validate_source_pose(value["source_pose"])
    _validate_targets(value["targets"])
    rules = value["rules"]
    if not isinstance(rules, list) or len(rules) != RULE_COUNT:
        raise CommandError("semantic pose command must contain exactly 18 semantic rules")
    selectors: set[tuple[str, Any, tuple[str, ...]]] = set()
    for index, rule in enumerate(rules):
        _validate_rule(rule, index, selectors)
    if len(selectors) != RULE_COUNT:
        raise CommandError("semantic pose command does not cover exactly 18 semantic selectors")
    _validate_frame(value["identity_frame"])
    if len(_canonical_json(value)) > MAX_COMMAND_BYTES:
        raise CommandError(f"semantic pose command exceeds the bounded size of {MAX_COMMAND_BYTES} bytes")
    return value


def _load_pose_source(gallery: Path, expected: dict[str, Any]) -> dict[str, Any]:
    carrier = _load_carrier_module()
    try:
        bytes_value = carrier._read_regular_file(gallery / POSE_FILE, carrier.MAX_POSE_BYTES, "shared pose")
    except Exception as exc:
        raise CommandError(f"shared pose source could not be read: {exc}") from exc
    actual_sha = hashlib.sha256(bytes_value).hexdigest()
    if actual_sha != expected["sha256"]:
        raise CommandError("shared pose source SHA-256 disagrees with the validated carrier")
    try:
        value = json.loads(
            bytes_value.decode("utf-8"),
            object_pairs_hook=carrier._unique_object,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
        carrier._finite_json(value, "shared pose")
    except Exception as exc:
        raise CommandError("shared pose source is not valid finite JSON") from exc
    # The gallery's shared-pose file is an exact hash-bound source artifact;
    # unlike the command transport, its existing pretty-printed JSON bytes are
    # not rewritten or required to be command-canonical.
    required = {"format", "pose_id", "version", "convention", "solver", "rules"}
    if not isinstance(value, dict) or set(value) != required:
        raise CommandError("shared pose source has unexpected or missing fields")
    if value["format"] != POSE_FORMAT or value["pose_id"] != expected["pose_id"] or value["version"] != POSE_VERSION:
        raise CommandError("shared pose source identity is invalid")
    convention = value["convention"]
    if (
        not isinstance(convention, dict)
        or set(convention) != {"vectors", "bind_transform", "skin_transform", "rotation_storage", "quaternion_decimal_places"}
        or convention["vectors"] != "column"
        or convention["rotation_storage"] != "xyzw"
        or type(convention["quaternion_decimal_places"]) is not int
        or convention["quaternion_decimal_places"] != POSE_QUATERNION_DECIMAL_PLACES
    ):
        raise CommandError("shared pose source transform convention is invalid")
    if value["solver"] != {"ik": False, "contact": False}:
        raise CommandError("shared pose source must explicitly disable IK and contact")
    source_rules = value["rules"]
    if not isinstance(source_rules, list) or len(source_rules) != RULE_COUNT:
        raise CommandError("shared pose source must contain exactly 18 rules")
    normalized: list[dict[str, Any]] = []
    selectors: set[tuple[str, Any, tuple[str, ...]]] = set()
    for index, source_rule in enumerate(source_rules):
        if not isinstance(source_rule, dict) or set(source_rule) != {
            "kind",
            "role",
            "anchors",
            "axis",
            "angle_degrees",
            "rotation_xyzw",
        }:
            raise CommandError(f"shared pose source rule {index} has unexpected or missing fields")
        axis = source_rule["axis"]
        if axis not in {"identity", "x", "z"}:
            raise CommandError(f"shared pose source rule {index} has an unsupported axis")
        angle = _finite_number(source_rule["angle_degrees"], f"shared pose source rule {index}.angle_degrees")
        rotation = source_rule["rotation_xyzw"]
        if not isinstance(rotation, list) or len(rotation) != 4:
            raise CommandError(f"shared pose source rule {index} rotation is not a four-vector")
        components = [
            _finite_number(item, f"shared pose source rule {index}.rotation_xyzw[{n}]")
            for n, item in enumerate(rotation)
        ]
        norm = math.sqrt(sum(component * component for component in components))
        if abs(norm - 1.0) > UNIT_TOLERANCE:
            raise CommandError(f"shared pose source rule {index} rotation is not unit length")
        half_angle = math.radians(angle) * 0.5
        if axis == "identity":
            expected_rotation = (0.0, 0.0, 0.0, 1.0)
        elif axis == "x":
            expected_rotation = (math.sin(half_angle), 0.0, 0.0, math.cos(half_angle))
        else:
            expected_rotation = (0.0, 0.0, math.sin(half_angle), math.cos(half_angle))
        if max(abs(actual - expected) for actual, expected in zip(components, expected_rotation)) > POSE_QUATERNION_TOLERANCE:
            raise CommandError(f"shared pose source rule {index} rotation is not bound to its source recipe")
        role = source_rule["role"]
        anchors = source_rule["anchors"]
        if type(source_rule["kind"]) is not str or (role is not None and type(role) is not str) or not isinstance(anchors, list) or any(type(anchor) is not str for anchor in anchors):
            raise CommandError(f"shared pose source rule {index} selector fields are invalid")
        selector = _selector(source_rule["kind"], role, anchors)
        if selector in selectors:
            raise CommandError("shared pose source contains duplicate semantic selectors")
        selectors.add(selector)
        normalized.append(
            {
                "kind": source_rule["kind"],
                "role": role,
                "anchors": list(anchors),
                "rotation_xyzw": list(rotation),
            }
        )
    return {
        "format": value["format"],
        "pose_id": value["pose_id"],
        "version": value["version"],
        "sha256": actual_sha,
        "rules": normalized,
    }


def _validated_carrier(gallery: Path, carrier_path: Path) -> tuple[Any, dict[str, Any], dict[str, Any], tuple[str, str], tuple[str, str]]:
    carrier_module = _load_carrier_module()
    try:
        carrier = carrier_module.load_carrier(carrier_path)
        payload, profile_ids, instance_ids = carrier_module.validate_carrier(carrier, gallery)
    except carrier_module.CarrierError as exc:
        raise CommandError(f"disposable avatar carrier rejected: {exc}") from exc
    return carrier_module, carrier, payload, profile_ids, instance_ids


def build_command(gallery: Path, carrier_path: Path) -> dict[str, Any]:
    """Build one command from a freshly validated carrier and exact pose source."""
    gallery = Path(gallery)
    carrier_path = Path(carrier_path)
    if not gallery.is_absolute() or not carrier_path.is_absolute():
        raise CommandError("gallery and carrier paths must be absolute")
    carrier_module, carrier, payload, _, _ = _validated_carrier(gallery, carrier_path)
    shared_pose = carrier.get("shared_pose")
    if not isinstance(shared_pose, dict) or set(shared_pose) != set(carrier_module.SHARED_POSE_KEYS):
        raise CommandError("validated carrier shared-pose identity is incomplete")
    expected_pose = {
        "format": POSE_FORMAT,
        "pose_id": payload["pose_id"],
        "sha256": payload["pose_sha256"],
        "version": POSE_VERSION,
    }
    if shared_pose["path"] != POSE_FILE or shared_pose["pose_id"] != expected_pose["pose_id"] or shared_pose["sha256"] != expected_pose["sha256"]:
        raise CommandError("validated carrier shared-pose identity does not match the gallery projection")
    source = _load_pose_source(gallery, expected_pose)
    if source["format"] != expected_pose["format"] or source["pose_id"] != expected_pose["pose_id"] or source["sha256"] != expected_pose["sha256"] or source["version"] != expected_pose["version"]:
        raise CommandError("shared pose source identity does not match the validated carrier")
    targets = [
        {
            "instance_id": instance["instance_id"],
            "profile_id": instance["profile_id"],
            "candidate_profile_sha256": instance["candidate_profile_sha256"],
        }
        for instance in carrier["instances"]
    ]
    command = {
        "schema": SCHEMA,
        "boundary": BOUNDARY,
        "command_id": COMMAND_ID,
        "command_version": COMMAND_VERSION,
        "source_pose": {
            "format": source["format"],
            "pose_id": source["pose_id"],
            "sha256": source["sha256"],
            "version": source["version"],
        },
        "targets": targets,
        "rules": source["rules"],
        "identity_frame": json.loads(json.dumps(IDENTITY_FRAME)),
    }
    return _validate_shape(command)


def load_command(path: Path) -> dict[str, Any]:
    """Load one canonical command file and validate its local shape."""
    carrier = _load_carrier_module()
    try:
        data = carrier._read_regular_file(Path(path), MAX_COMMAND_BYTES, "semantic pose command")
    except Exception as exc:
        raise CommandError(f"semantic pose command could not be read: {exc}") from exc
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=carrier._unique_object,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
        carrier._finite_json(value, "semantic pose command")
    except Exception as exc:
        raise CommandError(f"semantic pose command is not valid finite UTF-8 JSON: {path}") from exc
    if data != _canonical_json(value):
        raise CommandError("semantic pose command is not canonical newline-terminated JSON")
    return _validate_shape(value)


def validate_command(command: Any, gallery: Path, carrier_path: Path) -> dict[str, Any]:
    """Rebuild and compare a command against the fresh carrier/gallery lineage."""
    _validate_shape(command)
    expected = build_command(gallery, carrier_path)
    if not _exact_equal(command, expected):
        raise CommandError("semantic pose command does not exactly match the validated carrier and gallery")
    return command


def command_identity(command: dict[str, Any]) -> dict[str, Any]:
    _validate_shape(command)
    canonical = _canonical_json(command)
    return {
        "sha256": hashlib.sha256(canonical).hexdigest(),
        "byte_count_decimal": str(len(canonical)),
        "schema": command["schema"],
        "boundary": command["boundary"],
        "command_id": command["command_id"],
        "command_version": command["command_version"],
    }


def semantic_payload(command: dict[str, Any]) -> dict[str, Any]:
    _validate_shape(command)
    return {"rules": command["rules"], "identity_frame": command["identity_frame"]}


def write_command(path: Path, command: dict[str, Any]) -> None:
    """Publish canonical command bytes through the existing safe atomic writer."""
    _validate_shape(command)
    canonical = _canonical_json(command)
    if len(canonical) > MAX_COMMAND_BYTES:
        raise CommandError(f"semantic pose command exceeds the bounded size of {MAX_COMMAND_BYTES} bytes")
    try:
        _load_carrier_module().write_carrier(path, command)
    except Exception as exc:
        raise CommandError(f"semantic pose command could not be published: {exc}") from exc


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="operation", required=True)
    build = subparsers.add_parser("build", help="build and atomically publish a command")
    build.add_argument("--gallery", required=True, type=Path, help="absolute completed structural gallery directory")
    build.add_argument("--carrier", required=True, type=Path, help="absolute validated disposable avatar carrier path")
    build.add_argument("--output", required=True, type=Path, help="absolute command output path")
    validate = subparsers.add_parser("validate", help="load and validate one command against carrier and gallery")
    validate.add_argument("--gallery", required=True, type=Path, help="absolute completed structural gallery directory")
    validate.add_argument("--carrier", required=True, type=Path, help="absolute validated disposable avatar carrier path")
    validate.add_argument("--command", required=True, type=Path, help="absolute canonical command path")
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        _load_carrier_module()
        if args.operation == "build":
            command = build_command(args.gallery, args.carrier)
            write_command(args.output, command)
        else:
            command = load_command(args.command)
            validate_command(command, args.gallery, args.carrier)
    except (CommandError, ValueError, OSError, TypeError) as exc:
        print(f"disposable semantic pose command failed: {exc}", file=sys.stderr)
        return 2
    print(_canonical_json(command).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build a bounded, non-rendered CK evidence projection for two avatars.

This is deliberately an experiment artifact.  It composes already validated
gallery/carrier identities with one minimal Rust structural inspection per
selected source; it does not define a runtime package or generate geometry.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import selectors
import subprocess
import sys
import time
from typing import Any


sys.dont_write_bytecode = True


SCHEMA = "creature-kernel.disposable-ck-rust-projection.v1"
BOUNDARY = "experiment_local_ck_projection_evidence_only"
POSE_FILE = "structural_embodiment_shared_pose.json"
SOURCE_DIR = "sources"
SOURCE_MAX_BYTES = 16 * 1024 * 1024
MAX_CLI_BYTES = 128 * 1024 * 1024
MAX_PROJECTION_BYTES = 4 * 1024 * 1024
MAX_RUST_STDOUT_BYTES = 2 * 1024 * 1024
MAX_RUST_STDERR_BYTES = 64 * 1024
RUST_TIMEOUT_SECONDS = 120
MAX_JSON_NODES = 200_000
MAX_JSON_DEPTH = 96
MAX_STRING_LENGTH = 65_536
MAX_SOURCE_DEPENDENCIES = 4_096
MAX_GRAPH_COLLECTION_ITEMS = 4_096
RUST_FORMAT = "creature-kernel.provisional-structural-inspection.v1"
RUST_OPERATION = "inspect-structure"
PROJECTION_IDENTITY_SCOPE = "canonical_transport_body_only_not_provenance"
HASH_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
DEPENDENCY_HASH_PATTERN = re.compile(r"sha256:[0-9a-f]{64}\Z")
FORBIDDEN_FIELD_TOKENS = {
    "adapter",
    "godot",
    "host",
    "package",
    "readiness",
}

PROJECTION_BODY_KEYS = (
    "schema",
    "boundary",
    "producer_identity",
    "carrier_identity",
    "gallery_identity",
    "shared_pose",
    "avatars",
)
PROJECTION_KEYS = (
    "schema",
    "boundary",
    "projection_identity",
    "producer_identity",
    "carrier_identity",
    "gallery_identity",
    "shared_pose",
    "avatars",
)
PROJECTION_IDENTITY_KEYS = ("scope", "sha256", "bytes")
PRODUCER_IDENTITY_KEYS = ("sha256", "bytes", "operation", "format")
CARRIER_IDENTITY_KEYS = ("schema", "boundary", "sha256", "bytes", "instance_ids")
GALLERY_IDENTITY_KEYS = ("projection_contract", "manifest_sha256", "manifest_bytes", "boundary", "profile_ids")
SHARED_POSE_KEYS = ("path", "pose_id", "sha256", "bytes")
AVATAR_KEYS = (
    "instance_id",
    "profile_id",
    "label",
    "candidate_profile_sha256",
    "source",
    "rust_inspection",
    "artifacts",
    "metrics",
)
SOURCE_KEYS = ("path", "sha256", "bytes", "document", "namespace")
ARTIFACT_KEYS = ("path", "sha256", "bytes")
RUST_KEYS = (
    "format",
    "operation",
    "stage",
    "status",
    "processing_complete",
    "diagnostics_complete",
    "diagnostics",
    "summary",
    "graph",
)
RUST_EVIDENCE_KEYS = (
    "format",
    "operation",
    "stage",
    "status",
    "processing_complete",
    "diagnostics_complete",
    "diagnostics",
    "summary",
    "source",
)
RUST_GRAPH_KEYS = (
    "projection",
    "contract",
    "source",
    "basis",
    "profiles",
    "extensions",
    "modules",
    "parts",
    "joints",
    "sockets",
    "attachments",
    "landmarks",
    "dimensions",
    "frames",
    "regions",
    "capabilities",
    "fields",
)
SUMMARY_KEYS = (
    "modules",
    "parts",
    "joints",
    "sockets",
    "attachments",
    "landmarks",
    "dimensions",
    "frames",
    "regions",
    "capabilities",
    "fields",
)


class ProjectionError(ValueError):
    """A bounded, fail-closed projection or publication failure."""


def _load_carrier_module():
    try:
        from disposable_avatar_carrier import (  # type: ignore
            load_carrier,
            validate_carrier,
            write_carrier,
        )
        import disposable_avatar_carrier as module  # type: ignore
    except ImportError:  # pragma: no cover - package import path
        from . import disposable_avatar_carrier as module  # type: ignore
        from .disposable_avatar_carrier import load_carrier, validate_carrier, write_carrier
    module.load_carrier = load_carrier
    module.validate_carrier = validate_carrier
    module.write_carrier = write_carrier
    return module


def _canonical_json(value: Any) -> bytes:
    try:
        return (
            json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise ProjectionError("projection cannot be encoded as canonical finite JSON") from exc


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON object key")
        value[key] = item
    return value


def _finite_json(value: Any, where: str = "projection", *, depth: int = 0, state: list[int] | None = None) -> None:
    if state is None:
        state = [0]
    state[0] += 1
    if state[0] > MAX_JSON_NODES:
        raise ProjectionError(f"{where} exceeds the bounded JSON node count")
    if depth > MAX_JSON_DEPTH:
        raise ProjectionError(f"{where} exceeds the bounded JSON depth")
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ProjectionError(f"{where} contains a non-finite number")
        return
    if isinstance(value, int) and not isinstance(value, bool):
        if abs(value) > 10**15:
            raise ProjectionError(f"{where} contains an unbounded integer")
        return
    if isinstance(value, str):
        if len(value) > MAX_STRING_LENGTH:
            raise ProjectionError(f"{where} contains an overlong string")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _finite_json(item, f"{where}[{index}]", depth=depth + 1, state=state)
        return
    if isinstance(value, dict):
        if len(value) > 2048:
            raise ProjectionError(f"{where} contains an oversized object")
        for key, item in value.items():
            if not isinstance(key, str) or len(key) > MAX_STRING_LENGTH:
                raise ProjectionError(f"{where} contains an invalid object key")
            _finite_json(item, f"{where}.{key}", depth=depth + 1, state=state)
        return
    if value is not None and not isinstance(value, bool):
        raise ProjectionError(f"{where} contains an unsupported JSON value")


def _exact_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return set(left) == set(right) and all(_exact_equal(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(_exact_equal(a, b) for a, b in zip(left, right))
    return left == right


def _absolute_path(path: Path, label: str) -> Path:
    path = Path(path)
    if not path.is_absolute():
        raise ProjectionError(f"{label} must be an absolute path: {path}")
    return path


def _object(value: Any, label: str, keys: tuple[str, ...]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ProjectionError(f"{label} has unexpected or missing fields")
    return value


def _string(value: Any, label: str) -> str:
    if type(value) is not str or not value or len(value) > MAX_STRING_LENGTH:
        raise ProjectionError(f"{label} must be a bounded non-empty string")
    return value


def _integer(value: Any, label: str, *, maximum: int = MAX_PROJECTION_BYTES * 4) -> int:
    if type(value) is not int or value < 0 or value > maximum:
        raise ProjectionError(f"{label} must be a bounded non-negative integer")
    return value


def _hash(value: Any, label: str) -> str:
    value = _string(value, label)
    if HASH_PATTERN.fullmatch(value) is None:
        raise ProjectionError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _dependency_hash(value: Any, label: str) -> str:
    value = _string(value, label)
    if DEPENDENCY_HASH_PATTERN.fullmatch(value) is None:
        raise ProjectionError(f"{label} must be sha256: plus 64 lowercase hex characters")
    return value


def _relative_path(value: Any, label: str) -> str:
    value = _string(value, label)
    if value.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:[\\/]", value) or "\\" in value:
        raise ProjectionError(f"{label} must be a safe relative POSIX path")
    parsed = PurePosixPath(value)
    if parsed.is_absolute() or not value or any(part in {"", ".", ".."} for part in parsed.parts):
        raise ProjectionError(f"{label} must be a safe relative POSIX path")
    return value


def _reject_forbidden_fields(value: Any, where: str = "projection") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = key.lower().replace("-", "_")
            if any(normalized == token or normalized.startswith(token + "_") for token in FORBIDDEN_FIELD_TOKENS):
                raise ProjectionError(f"{where} contains a forbidden field: {key}")
            _reject_forbidden_fields(item, f"{where}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_forbidden_fields(item, f"{where}[{index}]")


def _reject_absolute_strings(value: Any, where: str = "projection") -> None:
    if isinstance(value, str):
        if value.startswith(("/", "\\", "file://")) or re.match(r"^[A-Za-z]:[\\/]", value):
            raise ProjectionError(f"{where} contains an absolute path")
    elif isinstance(value, dict):
        for key, item in value.items():
            _reject_absolute_strings(item, f"{where}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_absolute_strings(item, f"{where}[{index}]")


def _read_regular_file(carrier_module: Any, path: Path, maximum: int, label: str) -> bytes:
    try:
        return carrier_module._read_regular_file(path, maximum, label)
    except Exception as exc:
        if isinstance(exc, ProjectionError):
            raise
        raise ProjectionError(f"{label} could not be read safely: {type(exc).__name__}: {exc}") from exc


def _artifact_names(carrier_module: Any) -> tuple[str, ...]:
    try:
        names = tuple(carrier_module.preflight.__globals__["EXPECTED_ARTIFACT_NAMES"])
    except (AttributeError, KeyError, TypeError) as exc:
        raise ProjectionError("existing gallery validator did not expose its artifact contract") from exc
    if len(names) != 6 or any(type(name) is not str for name in names):
        raise ProjectionError("existing gallery validator artifact contract is not exactly six names")
    return names


def _validate_artifacts(value: Any, profile_id: str, carrier_module: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) != 6:
        raise ProjectionError(f"{label} must contain exactly six existing artifact references")
    expected_names = _artifact_names(carrier_module)
    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        record = _object(item, f"{label}[{index}]", ARTIFACT_KEYS)
        path = _relative_path(record["path"], f"{label}[{index}].path")
        expected_path = f"{profile_id}/{expected_names[index]}"
        if path != expected_path:
            raise ProjectionError(f"{label}[{index}] is not the expected existing artifact reference")
        result.append({"path": path, "sha256": _hash(record["sha256"], f"{label}[{index}].sha256"), "bytes": _integer(record["bytes"], f"{label}[{index}].bytes")})
    return result


def _validate_summary(value: Any, label: str) -> dict[str, int]:
    summary = _object(value, label, SUMMARY_KEYS)
    for key in SUMMARY_KEYS:
        _integer(summary[key], f"{label}.{key}", maximum=MAX_GRAPH_COLLECTION_ITEMS)
    return summary


def _validate_source_identity(value: Any, label: str) -> dict[str, Any]:
    source = _object(value, label, ("dependencies", "document", "namespace"))
    dependencies = source["dependencies"]
    if not isinstance(dependencies, list) or len(dependencies) > MAX_SOURCE_DEPENDENCIES:
        raise ProjectionError(f"{label}.dependencies exceeds its bounded array shape")
    for index, dependency in enumerate(dependencies):
        item = _object(dependency, f"{label}.dependencies[{index}]", ("document", "namespace", "content_sha256"))
        _string(item["document"], f"{label}.dependencies[{index}].document")
        _string(item["namespace"], f"{label}.dependencies[{index}].namespace")
        _dependency_hash(item["content_sha256"], f"{label}.dependencies[{index}].content_sha256")
    _string(source["document"], f"{label}.document")
    _string(source["namespace"], f"{label}.namespace")
    return source


def _validate_rust_result_fields(root: dict[str, Any], label: str) -> None:
    if root["format"] != RUST_FORMAT or root["operation"] != RUST_OPERATION:
        raise ProjectionError(f"{label} is not the existing inspect-structure output")
    if root["stage"] != "structural-validation" or root["status"] != "success":
        raise ProjectionError(f"{label} is not a successful structural inspection")
    if root["processing_complete"] is not True or root["diagnostics_complete"] is not True or root["diagnostics"] != []:
        raise ProjectionError(f"{label} completion flags or diagnostics are invalid")


def _validate_rust_inspection(value: Any, label: str = "rust_inspection") -> dict[str, Any]:
    root = _object(value, label, RUST_KEYS)
    _validate_rust_result_fields(root, label)
    summary = _validate_summary(root["summary"], f"{label}.summary")
    graph = _object(root["graph"], f"{label}.graph", RUST_GRAPH_KEYS)
    if graph["projection"] != "source-preserving-provisional-structural-debug":
        raise ProjectionError(f"{label}.graph has an unsupported projection")
    contract = _object(graph["contract"], f"{label}.graph.contract", ("family", "revision"))
    if contract["family"] != "creature-kernel.body" or type(contract["revision"]) is not int or contract["revision"] != 1:
        raise ProjectionError(f"{label}.graph.contract is not the supported body contract")
    basis = _object(graph["basis"], f"{label}.graph.basis", ("length_unit", "handedness", "up", "forward"))
    if basis != {"length_unit": "metre", "handedness": "right", "up": "+y", "forward": "+z"}:
        raise ProjectionError(f"{label}.graph.basis is not the supported structural basis")
    profiles = _object(graph["profiles"], f"{label}.graph.profiles", ("semantic_numeric",))
    if profiles["semantic_numeric"] != "ck.numeric-frame.r1":
        raise ProjectionError(f"{label}.graph.profiles is not the supported semantic numeric profile")
    source = _validate_source_identity(graph["source"], f"{label}.graph.source")
    extensions = graph["extensions"]
    if not isinstance(extensions, list) or len(extensions) > MAX_GRAPH_COLLECTION_ITEMS:
        raise ProjectionError(f"{label}.graph.extensions must be a bounded array")
    for key in SUMMARY_KEYS:
        collection = graph[key]
        if not isinstance(collection, list) or len(collection) > MAX_GRAPH_COLLECTION_ITEMS:
            raise ProjectionError(f"{label}.graph.{key} must be a bounded array")
        if summary[key] != len(collection):
            raise ProjectionError(f"{label}.summary.{key} disagrees with graph collection length")
    _finite_json(root, label)
    return {
        "format": root["format"],
        "operation": root["operation"],
        "stage": root["stage"],
        "status": root["status"],
        "processing_complete": root["processing_complete"],
        "diagnostics_complete": root["diagnostics_complete"],
        "diagnostics": root["diagnostics"],
        "summary": summary,
        "source": source,
    }


def _validate_rust_evidence(value: Any, label: str = "rust_inspection") -> dict[str, Any]:
    evidence = _object(value, label, RUST_EVIDENCE_KEYS)
    _validate_rust_result_fields(evidence, label)
    _validate_summary(evidence["summary"], f"{label}.summary")
    _validate_source_identity(evidence["source"], f"{label}.source")
    _finite_json(evidence, label)
    _reject_forbidden_fields(evidence, label)
    return evidence


def _validated_cli_producer(carrier_module: Any, cli_path: Path | None) -> tuple[Path, bytes, dict[str, Any]]:
    if cli_path is None:
        raise ProjectionError("an explicit absolute Rust CLI path is required")
    cli_path = _absolute_path(cli_path, "Rust CLI path")
    try:
        info = carrier_module._regular_file(cli_path, "Rust CLI path")
    except Exception as exc:
        raise ProjectionError(f"Rust CLI path is not a regular non-symlink file: {type(exc).__name__}: {exc}") from exc
    if info.st_mode & 0o111 == 0 or not os.access(cli_path, os.X_OK):
        raise ProjectionError(f"Rust CLI path is not executable: {cli_path}")
    data = _read_regular_file(carrier_module, cli_path, MAX_CLI_BYTES, "Rust CLI path")
    identity = {
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "operation": RUST_OPERATION,
        "format": RUST_FORMAT,
    }
    return cli_path, data, identity


def _stop_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    process.kill()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:  # pragma: no cover - defensive after SIGKILL
        pass


def _bounded_subprocess(command: list[str]) -> tuple[int, bytes, bytes]:
    """Run one command while retaining no more than the declared pipe limits."""
    try:
        process = subprocess.Popen(
            command,
            cwd=Path(__file__).resolve().parents[2],
            env=os.environ.copy(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as exc:
        raise ProjectionError(f"Rust inspect-structure subprocess failed: {type(exc).__name__}: {exc}") from exc
    if process.stdout is None or process.stderr is None:  # pragma: no cover - Popen contract
        _stop_process(process)
        raise ProjectionError("Rust inspect-structure subprocess did not expose bounded pipes")
    selector = selectors.DefaultSelector()
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    limits = {"stdout": MAX_RUST_STDOUT_BYTES, "stderr": MAX_RUST_STDERR_BYTES}
    deadline = time.monotonic() + RUST_TIMEOUT_SECONDS
    try:
        for stream, name in ((process.stdout, "stdout"), (process.stderr, "stderr")):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, name)
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _stop_process(process)
                raise ProjectionError(f"Rust inspect-structure timed out after {RUST_TIMEOUT_SECONDS} seconds")
            events = selector.select(min(0.1, remaining))
            for key, _ in events:
                stream = key.fileobj
                name = key.data
                try:
                    chunk = os.read(stream.fileno(), 65_536)
                except BlockingIOError:
                    continue
                if not chunk:
                    selector.unregister(stream)
                    stream.close()
                    continue
                remaining_capacity = limits[name] - len(buffers[name])
                if len(chunk) > remaining_capacity:
                    _stop_process(process)
                    raise ProjectionError(
                        f"Rust inspect-structure {name} exceeds the bounded limit of {limits[name]} bytes"
                    )
                buffers[name].extend(chunk)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            _stop_process(process)
            raise ProjectionError(f"Rust inspect-structure timed out after {RUST_TIMEOUT_SECONDS} seconds")
        try:
            return_code = process.wait(timeout=remaining)
        except subprocess.TimeoutExpired as exc:
            _stop_process(process)
            raise ProjectionError(f"Rust inspect-structure timed out after {RUST_TIMEOUT_SECONDS} seconds") from exc
        return return_code, bytes(buffers["stdout"]), bytes(buffers["stderr"])
    finally:
        selector.close()
        for stream in (process.stdout, process.stderr):
            if not stream.closed:
                stream.close()
        if process.poll() is None:
            _stop_process(process)


def _run_inspection(cli_path: Path, source_path: Path) -> dict[str, Any]:
    command = [os.fspath(cli_path), RUST_OPERATION, "--input", os.fspath(source_path)]
    return_code, stdout, stderr_bytes = _bounded_subprocess(command)
    if return_code != 0:
        stderr = stderr_bytes.decode("utf-8", "replace")[-512:]
        raise ProjectionError(f"Rust inspect-structure exited {return_code}: {stderr}")
    try:
        value = json.loads(
            stdout.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise ProjectionError("Rust inspect-structure did not return one valid JSON object") from exc
    return _validate_rust_inspection(value)


def _source_record(data: bytes, profile_id: str, inspection: dict[str, Any]) -> dict[str, Any]:
    relative = f"{SOURCE_DIR}/{profile_id}.json"
    try:
        parsed = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise ProjectionError(f"source {profile_id} is not valid finite UTF-8 JSON") from exc
    _finite_json(parsed, f"source {profile_id}")
    if not isinstance(parsed, dict) or not isinstance(parsed.get("source"), dict):
        raise ProjectionError(f"source {profile_id} has no source identity object")
    declared = _object(parsed["source"], f"source {profile_id}.source", ("dependencies", "document", "namespace"))
    if not isinstance(declared["dependencies"], list) or len(declared["dependencies"]) > MAX_SOURCE_DEPENDENCIES:
        raise ProjectionError(f"source {profile_id}.source.dependencies exceeds its bounded array shape")
    for index, dependency in enumerate(declared["dependencies"]):
        item = _object(dependency, f"source {profile_id}.source.dependencies[{index}]", ("document", "namespace", "content_sha256"))
        _string(item["document"], f"source {profile_id}.source.dependencies[{index}].document")
        _string(item["namespace"], f"source {profile_id}.source.dependencies[{index}].namespace")
        _dependency_hash(item["content_sha256"], f"source {profile_id}.source.dependencies[{index}].content_sha256")
    rust_source = inspection["source"]
    if not _exact_equal(declared, rust_source):
        raise ProjectionError(
            f"source {profile_id} identity and dependencies disagree with Rust inspect-structure evidence"
        )
    return {
        "path": relative,
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "document": rust_source["document"],
        "namespace": rust_source["namespace"],
    }


def _source_bytes(carrier_module: Any, gallery: Path, profile_id: str) -> bytes:
    return _read_regular_file(
        carrier_module,
        gallery / SOURCE_DIR / f"{profile_id}.json",
        SOURCE_MAX_BYTES,
        f"source {profile_id}",
    )


def _validated_carrier_state(carrier_module: Any, gallery: Path, carrier_path: Path, label: str) -> dict[str, Any]:
    try:
        carrier_value = carrier_module.load_carrier(carrier_path)
        payload, profile_ids, instance_ids = carrier_module.validate_carrier(carrier_value, gallery)
        carrier_bytes = carrier_module._read_carrier_bytes(carrier_path)
        canonical_carrier = carrier_module._canonical_json(carrier_value)
    except Exception as exc:
        raise ProjectionError(f"{label} carrier/gallery validation failed: {type(exc).__name__}: {exc}") from exc
    if carrier_bytes != canonical_carrier:
        raise ProjectionError(f"{label} carrier changed while its exact identity was being read")
    if not isinstance(carrier_value, dict) or not isinstance(payload, dict):
        raise ProjectionError(f"{label} carrier validator did not return object values")
    if len(profile_ids) != 2 or len(instance_ids) != 2:
        raise ProjectionError(f"{label} carrier validation did not return exactly two ordered identities")
    return {
        "carrier_value": carrier_value,
        "carrier_bytes": carrier_bytes,
        "payload": payload,
        "profile_ids": tuple(profile_ids),
        "instance_ids": tuple(instance_ids),
    }


def _require_unchanged_state(initial: dict[str, Any], final: dict[str, Any]) -> None:
    for key in ("carrier_value", "carrier_bytes", "payload", "profile_ids", "instance_ids"):
        if not _exact_equal(initial[key], final[key]):
            raise ProjectionError(f"carrier/gallery {key} changed during Rust inspection")


def build_projection(gallery: Path, carrier_path: Path, *, cli_path: Path | None = None) -> dict[str, Any]:
    """Freshly validate the carrier/gallery and compose exactly two avatars."""
    gallery = _absolute_path(gallery, "gallery path")
    carrier_path = _absolute_path(carrier_path, "carrier path")
    carrier_module = _load_carrier_module()
    cli_path, producer_bytes, producer_identity = _validated_cli_producer(carrier_module, cli_path)
    initial_state = _validated_carrier_state(carrier_module, gallery, carrier_path, "initial")
    carrier_value = initial_state["carrier_value"]
    carrier_bytes = initial_state["carrier_bytes"]
    payload = initial_state["payload"]
    profile_ids = initial_state["profile_ids"]
    instance_ids = initial_state["instance_ids"]
    profiles = payload.get("profiles")
    if not isinstance(profiles, list) or len(profiles) != 2:
        raise ProjectionError("carrier validator did not return exactly two profiles")
    if tuple(profile.get("profile_id") for profile in profiles if isinstance(profile, dict)) != tuple(profile_ids):
        raise ProjectionError("carrier validator profile ordering is inconsistent")
    source_gallery = carrier_value.get("source_gallery")
    shared_pose = carrier_value.get("shared_pose")
    instances = carrier_value.get("instances")
    if not isinstance(source_gallery, dict) or not isinstance(shared_pose, dict) or not isinstance(instances, list):
        raise ProjectionError("validated carrier is missing its identity projections")
    if len(instances) != 2:
        raise ProjectionError("validated carrier must contain exactly two instances")
    source_bytes_by_profile = {
        profile_id: _source_bytes(carrier_module, gallery, profile_id)
        for profile_id in profile_ids
    }
    avatars = []
    for index, (profile, instance_id, profile_id) in enumerate(zip(profiles, instance_ids, profile_ids)):
        if not isinstance(profile, dict) or not isinstance(instances[index], dict):
            raise ProjectionError(f"validated carrier profile {index} is not an object")
        source_bytes = source_bytes_by_profile[profile_id]
        inspection = _run_inspection(cli_path, gallery / SOURCE_DIR / f"{profile_id}.json")
        if source_bytes != _source_bytes(carrier_module, gallery, profile_id):
            raise ProjectionError(f"source {profile_id} changed during Rust inspection")
        source = _source_record(source_bytes, profile_id, inspection)
        artifacts = _validate_artifacts(profile.get("artifacts"), profile_id, carrier_module, f"profile {profile_id}.artifacts")
        avatars.append(
            {
                "instance_id": instance_id,
                "profile_id": profile_id,
                "label": _string(profile.get("label"), f"profile {profile_id}.label"),
                "candidate_profile_sha256": _hash(profile.get("candidate_profile_sha256"), f"profile {profile_id}.candidate_profile_sha256"),
                "source": source,
                "rust_inspection": inspection,
                "artifacts": artifacts,
                "metrics": profile.get("metrics"),
            }
        )
    final_state = _validated_carrier_state(carrier_module, gallery, carrier_path, "post-inspection")
    _require_unchanged_state(initial_state, final_state)
    for profile_id, source_bytes in source_bytes_by_profile.items():
        if source_bytes != _source_bytes(carrier_module, gallery, profile_id):
            raise ProjectionError(f"source {profile_id} changed before post-inspection validation completed")
    _, final_producer_bytes, final_producer_identity = _validated_cli_producer(carrier_module, cli_path)
    if producer_bytes != final_producer_bytes or not _exact_equal(producer_identity, final_producer_identity):
        raise ProjectionError("Rust CLI executable changed during projection construction")
    projection_body = {
        "schema": SCHEMA,
        "boundary": BOUNDARY,
        "producer_identity": producer_identity,
        "carrier_identity": {
            "schema": carrier_value.get("schema"),
            "boundary": carrier_value.get("boundary"),
            "sha256": hashlib.sha256(carrier_bytes).hexdigest(),
            "bytes": len(carrier_bytes),
            "instance_ids": list(instance_ids),
        },
        "gallery_identity": {
            "projection_contract": source_gallery.get("projection_contract"),
            "manifest_sha256": source_gallery.get("manifest_sha256"),
            "manifest_bytes": source_gallery.get("manifest_bytes"),
            "boundary": source_gallery.get("boundary"),
            "profile_ids": list(profile_ids),
        },
        "shared_pose": dict(shared_pose),
        "avatars": avatars,
    }
    return identify_projection(projection_body, carrier_module=carrier_module)


def _validate_projection_body(value: Any, carrier_module: Any | None = None) -> dict[str, Any]:
    root = _object(value, "projection body", PROJECTION_BODY_KEYS)
    if root["schema"] != SCHEMA or root["boundary"] != BOUNDARY:
        raise ProjectionError("projection schema or experiment boundary is invalid")
    carrier_module = carrier_module or _load_carrier_module()
    producer = _object(root["producer_identity"], "producer_identity", PRODUCER_IDENTITY_KEYS)
    _hash(producer["sha256"], "producer_identity.sha256")
    _integer(producer["bytes"], "producer_identity.bytes", maximum=MAX_CLI_BYTES)
    if producer["operation"] != RUST_OPERATION or producer["format"] != RUST_FORMAT:
        raise ProjectionError("producer_identity does not identify the exact inspect-structure producer contract")
    carrier = _object(root["carrier_identity"], "carrier_identity", CARRIER_IDENTITY_KEYS)
    if carrier["schema"] != carrier_module.SCHEMA or carrier["boundary"] != carrier_module.BOUNDARY:
        raise ProjectionError("carrier_identity schema or boundary does not match the existing carrier")
    _hash(carrier["sha256"], "carrier_identity.sha256")
    _integer(carrier["bytes"], "carrier_identity.bytes")
    if not isinstance(carrier["instance_ids"], list) or len(carrier["instance_ids"]) != 2:
        raise ProjectionError("carrier_identity.instance_ids must contain exactly two IDs")
    for index, item in enumerate(carrier["instance_ids"]):
        _string(item, f"carrier_identity.instance_ids[{index}]")
        if carrier_module.INSTANCE_ID_PATTERN.fullmatch(item) is None:
            raise ProjectionError(f"carrier_identity.instance_ids[{index}] does not match the carrier identity pattern")
    if len(set(carrier["instance_ids"])) != 2:
        raise ProjectionError("carrier_identity.instance_ids must be distinct")
    gallery = _object(root["gallery_identity"], "gallery_identity", GALLERY_IDENTITY_KEYS)
    _string(gallery["projection_contract"], "gallery_identity.projection_contract")
    _hash(gallery["manifest_sha256"], "gallery_identity.manifest_sha256")
    _integer(gallery["manifest_bytes"], "gallery_identity.manifest_bytes")
    _string(gallery["boundary"], "gallery_identity.boundary")
    if not isinstance(gallery["profile_ids"], list) or len(gallery["profile_ids"]) != 2:
        raise ProjectionError("gallery_identity.profile_ids must contain exactly two IDs")
    for index, item in enumerate(gallery["profile_ids"]):
        _string(item, f"gallery_identity.profile_ids[{index}]")
    if len(set(gallery["profile_ids"])) != 2:
        raise ProjectionError("gallery_identity.profile_ids must be distinct")
    pose = _object(root["shared_pose"], "shared_pose", SHARED_POSE_KEYS)
    _relative_path(pose["path"], "shared_pose.path")
    if pose["path"] != POSE_FILE:
        raise ProjectionError("shared_pose.path is not the existing shared pose artifact")
    _string(pose["pose_id"], "shared_pose.pose_id")
    _hash(pose["sha256"], "shared_pose.sha256")
    _integer(pose["bytes"], "shared_pose.bytes")
    avatars = root["avatars"]
    if not isinstance(avatars, list) or len(avatars) != 2:
        raise ProjectionError("projection must contain exactly two ordered avatars")
    profile_ids = tuple(gallery["profile_ids"])
    instance_ids = tuple(carrier["instance_ids"])
    for index, avatar in enumerate(avatars):
        record = _object(avatar, f"avatars[{index}]", AVATAR_KEYS)
        if record["instance_id"] != instance_ids[index] or record["profile_id"] != profile_ids[index]:
            raise ProjectionError("avatar identity ordering is inconsistent")
        _string(record["instance_id"], f"avatars[{index}].instance_id")
        _string(record["profile_id"], f"avatars[{index}].profile_id")
        _string(record["label"], f"avatars[{index}].label")
        _hash(record["candidate_profile_sha256"], f"avatars[{index}].candidate_profile_sha256")
        source = _object(record["source"], f"avatars[{index}].source", SOURCE_KEYS)
        expected_source_path = f"{SOURCE_DIR}/{profile_ids[index]}.json"
        if _relative_path(source["path"], f"avatars[{index}].source.path") != expected_source_path:
            raise ProjectionError("avatar source path is not the canonical generated source reference")
        _hash(source["sha256"], f"avatars[{index}].source.sha256")
        _integer(source["bytes"], f"avatars[{index}].source.bytes")
        _string(source["document"], f"avatars[{index}].source.document")
        _string(source["namespace"], f"avatars[{index}].source.namespace")
        evidence = _validate_rust_evidence(record["rust_inspection"], f"avatars[{index}].rust_inspection")
        if source["document"] != evidence["source"]["document"] or source["namespace"] != evidence["source"]["namespace"]:
            raise ProjectionError("source identity does not exactly match Rust inspect-structure evidence")
        _validate_artifacts(record["artifacts"], profile_ids[index], carrier_module, f"avatars[{index}].artifacts")
        if not isinstance(record["metrics"], dict):
            raise ProjectionError(f"avatars[{index}].metrics must be an object")
        _finite_json(record["metrics"], f"avatars[{index}].metrics")
    _finite_json(root)
    _reject_forbidden_fields(root)
    _reject_absolute_strings(root)
    encoded = _canonical_json(root)
    if len(encoded) > MAX_PROJECTION_BYTES:
        raise ProjectionError(f"projection body exceeds the bounded size of {MAX_PROJECTION_BYTES} bytes")
    return root


def _transport_identity(body: dict[str, Any]) -> dict[str, Any]:
    canonical = _canonical_json(body)
    return {
        "scope": PROJECTION_IDENTITY_SCOPE,
        "sha256": hashlib.sha256(canonical).hexdigest(),
        "bytes": len(canonical),
    }


def identify_projection(value: Any, *, carrier_module: Any | None = None) -> dict[str, Any]:
    """Attach transport identity only; this performs no fresh provenance validation."""
    if not isinstance(value, dict):
        raise ProjectionError("projection to identify must be an object")
    if set(value) not in (set(PROJECTION_BODY_KEYS), set(PROJECTION_KEYS)):
        raise ProjectionError("projection to identify has unexpected or missing fields")
    body = {key: value[key] for key in PROJECTION_BODY_KEYS if key in value}
    _validate_projection_body(body, carrier_module)
    identity = _transport_identity(body)
    return {
        "schema": body["schema"],
        "boundary": body["boundary"],
        "projection_identity": identity,
        "producer_identity": body["producer_identity"],
        "carrier_identity": body["carrier_identity"],
        "gallery_identity": body["gallery_identity"],
        "shared_pose": body["shared_pose"],
        "avatars": body["avatars"],
    }


def _validate_projection_shape(value: Any, carrier_module: Any | None = None) -> dict[str, Any]:
    root = _object(value, "projection", PROJECTION_KEYS)
    body = {key: root[key] for key in PROJECTION_BODY_KEYS}
    _validate_projection_body(body, carrier_module)
    identity = _object(root["projection_identity"], "projection_identity", PROJECTION_IDENTITY_KEYS)
    if identity["scope"] != PROJECTION_IDENTITY_SCOPE:
        raise ProjectionError("projection_identity does not declare its transport-only scope")
    _hash(identity["sha256"], "projection_identity.sha256")
    _integer(identity["bytes"], "projection_identity.bytes", maximum=MAX_PROJECTION_BYTES)
    if not _exact_equal(identity, _transport_identity(body)):
        raise ProjectionError("projection_identity does not match the canonical transport body")
    if len(_canonical_json(root)) > MAX_PROJECTION_BYTES:
        raise ProjectionError(f"projection exceeds the bounded size of {MAX_PROJECTION_BYTES} bytes")
    return root


def load_projection(path: Path) -> dict[str, Any]:
    carrier_module = _load_carrier_module()
    path = _absolute_path(path, "projection path")
    data = _read_regular_file(carrier_module, path, MAX_PROJECTION_BYTES, "projection path")
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise ProjectionError(f"projection is not valid finite UTF-8 JSON: {path}") from exc
    _validate_projection_shape(value, carrier_module)
    if data != _canonical_json(value):
        raise ProjectionError("projection JSON is not canonical newline-terminated JSON")
    return value


def validate_projection(path: Path, gallery: Path, carrier_path: Path, *, cli_path: Path | None = None) -> dict[str, Any]:
    stored = load_projection(path)
    expected = build_projection(gallery, carrier_path, cli_path=cli_path)
    if not _exact_equal(stored, expected):
        raise ProjectionError("projection does not exactly match fresh carrier/gallery/Rust evidence")
    return stored


def projection_identity(projection: dict[str, Any]) -> dict[str, Any]:
    """Return the embedded transport identity; it is not provenance evidence."""
    _validate_projection_shape(projection)
    return dict(projection["projection_identity"])


def write_projection(path: Path, projection: dict[str, Any]) -> None:
    """Mechanically publish a shape-valid, transport-identified projection without overwrite.

    This does not establish fresh carrier, gallery, source, or producer provenance;
    callers use ``validate_projection`` for that authoritative gate.
    """
    carrier_module = _load_carrier_module()
    _validate_projection_shape(projection, carrier_module)
    try:
        carrier_module.write_carrier(_absolute_path(path, "projection output path"), projection)
    except Exception as exc:
        raise ProjectionError(f"projection publication failed: {type(exc).__name__}: {exc}") from exc


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="operation", required=True)
    build = subparsers.add_parser("build")
    build.add_argument("--gallery", type=Path, required=True)
    build.add_argument("--carrier", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument(
        "--cli",
        type=Path,
        required=True,
        help="absolute regular non-symlink executable creature-kernel CLI path",
    )
    validate = subparsers.add_parser("validate")
    validate.add_argument("--gallery", type=Path, required=True)
    validate.add_argument("--carrier", type=Path, required=True)
    validate.add_argument("--projection", type=Path, required=True)
    validate.add_argument(
        "--cli",
        type=Path,
        required=True,
        help="absolute regular non-symlink executable creature-kernel CLI path",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.operation == "build":
            projection = build_projection(args.gallery, args.carrier, cli_path=args.cli)
            write_projection(args.output, projection)
            print(_canonical_json(projection).decode("utf-8"), end="")
        else:
            projection = validate_projection(args.projection, args.gallery, args.carrier, cli_path=args.cli)
            print(_canonical_json(projection).decode("utf-8"), end="")
    except ProjectionError as exc:
        print(f"projection-error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

#!/usr/bin/env python3
"""Publish the first disposable baseline-versus-successor surface checkpoint.

This is deliberately an adapter, not a surface renderer. It runs the current
v5 filled-form producer once, then the baseline and successor experiment
generators in isolated temporary storage. Both bundles are validated against
the same source and capture frame before four baseline/successor image pairs
are published into the existing immutable image-review format. The result is
for visual appraisal only; it is not production geometry or acceptance
evidence.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
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


SURFACE_PREVIEW_FORMAT = "creature-kernel.disposable-surface-preview.v2"
REGIONAL_GUIDE_FORMAT = "creature-kernel.disposable-surface-preview-regional-guide.v4"
SUCCESSOR_PREVIEW_FORMAT = "creature-kernel.disposable-successor-surface-preview.v2"
SUCCESSOR_MANIFEST_NAME = "successor-surface-manifest.json"
SUCCESSOR_CONSUMER_ID = "successor-surface-v1"
SUCCESSOR_REGION_ID = "successor-torso-shoulder-head-neck-limb-extremity-tail-profile-sweeps-v6"
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
MAX_MANIFEST_BYTES = 256 * 1024
MAX_GUIDE_BYTES = 512 * 1024
MAX_METRICS_BYTES = 256 * 1024
MAX_ARTIFACT_BYTES = 16 * 1024 * 1024
SOURCE_EVIDENCE_ENCODING = "utf-8"
SOURCE_EVIDENCE_TRANSFER = "base64"
SOURCE_EVIDENCE_COMPRESSION = "zlib"
INPUT_EVIDENCE_PREFIX = "input_body_document"
PRODUCER_EVIDENCE_PREFIX = "producer_v5"
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
EXPECTED_CANVAS = {"width": 1800, "height": 570, "mode": "RGB"}
EXPECTED_PROJECTIONS = [
    {"name": "front", "basis": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]], "base": "x-right/y-up/z-depth"},
    {"name": "side", "basis": [[0.0, 0.0, -1.0], [0.0, 1.0, 0.0], [1.0, 0.0, 0.0]], "base": "-z-right/y-up/x-depth"},
    {"name": "three-quarter", "basis": [[0.7071067811865475, 0.0, -0.7071067811865475], [0.0, 1.0, 0.0], [0.7071067811865475, 0.0, 0.7071067811865475]], "base": "front-right/y-up/depth"},
]
EXPECTED_LAYOUT = {
    "panel_order": ["front-guide", "front-skin", "side-guide", "side-skin", "three-quarter-guide", "three-quarter-skin"],
    "panels": [
        {"id": "front-guide", "projection": "front", "content": "guide", "box": [12, 72, 292, 548]},
        {"id": "front-skin", "projection": "front", "content": "skin", "box": [310, 72, 590, 548]},
        {"id": "side-guide", "projection": "side", "content": "guide", "box": [608, 72, 888, 548]},
        {"id": "side-skin", "projection": "side", "content": "skin", "box": [906, 72, 1186, 548]},
        {"id": "three-quarter-guide", "projection": "three-quarter", "content": "guide", "box": [1204, 72, 1484, 548]},
        {"id": "three-quarter-skin", "projection": "three-quarter", "content": "skin", "box": [1502, 72, 1782, 548]},
    ],
    "pairing": "guide-left/skin-right per projection",
    "frame": "shared-world-bounds-and-projection-basis",
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
    "head": 1,
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


def _evidence_fields(prefix: str) -> set[str]:
    return {
        f"{prefix}_zlib_base64",
        f"{prefix}_encoding",
        f"{prefix}_transfer",
        f"{prefix}_compression",
        f"{prefix}_bytes",
        f"{prefix}_sha256",
    }


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
        f"{prefix}_zlib_base64": base64.b64encode(
            zlib.compress(raw, level=9)
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
    encoded = value.get(f"{prefix}_zlib_base64")
    if not isinstance(encoded, str):
        raise SurfacePreviewPublishError(f"{where} has an invalid Base64 payload")
    try:
        compressed = base64.b64decode(encoded.encode("ascii"), validate=True)
    except (UnicodeEncodeError, ValueError) as exc:
        raise SurfacePreviewPublishError(f"{where} has an invalid Base64 payload") from exc
    decoder = zlib.decompressobj()
    try:
        raw = decoder.decompress(compressed, max_bytes + 1)
    except zlib.error as exc:
        raise SurfacePreviewPublishError(f"{where} has invalid compressed bytes") from exc
    if (
        len(raw) > max_bytes
        or decoder.unconsumed_tail
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
    raw = _decode_exact_evidence(
        value, prefix=prefix, max_bytes=max_bytes, where=where
    )
    if len(raw) != byte_count or hashlib.sha256(raw).hexdigest() != digest:
        raise SurfacePreviewPublishError(f"{where} does not bind its exact source bytes")
    try:
        common._metadata(value, where)
    except ValidationError as exc:
        raise SurfacePreviewPublishError(str(exc)) from exc
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
    value: Any, where: str = "source evidence"
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
        common._metadata(value, where)
    except ValidationError as exc:
        raise SurfacePreviewPublishError(str(exc)) from exc
    return value


def _read_producer_evidence(path: Path) -> dict[str, Any]:
    return _read_exact_evidence(
        path,
        prefix=PRODUCER_EVIDENCE_PREFIX,
        max_bytes=MAX_STDOUT_BYTES,
        where="v5 producer output",
    )


def _decode_producer_evidence(
    value: Any, where: str = "v5 producer evidence"
) -> bytes:
    return _decode_exact_evidence(
        value,
        prefix=PRODUCER_EVIDENCE_PREFIX,
        max_bytes=MAX_STDOUT_BYTES,
        where=where,
    )


def _validate_producer_evidence(
    value: Any, where: str = "v5 producer evidence"
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
        raise SurfacePreviewPublishError(f"{where} dimensions do not match the v2 canvas")
    if entry.get("width") != width or entry.get("height") != height:
        raise SurfacePreviewPublishError(f"{where} dimensions do not match inventory")
    mode = entry.get("mode")
    if mode != EXPECTED_CANVAS["mode"]:
        raise SurfacePreviewPublishError(f"{where}.mode does not match the v2 canvas")
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
    if entry.get("panels_per_view") != 2:
        raise SurfacePreviewPublishError(f"{where}.panels_per_view must be 2")
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


def _validate_controls(
    controls: Any,
    owners: list[dict[str, Any]],
    lower: list[float],
    upper: list[float],
) -> None:
    if not isinstance(controls, dict) or set(controls) != {"axes", "axial", "torso_cage", "shoulder_frame", "head", "limbs", "paws", "tails"}:
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
    expected_cage_fields = {"status", "owners", "axes", "orientation", "sections", "connections"}
    if not isinstance(torso_cage, dict) or set(torso_cage) != expected_cage_fields:
        raise SurfacePreviewPublishError("regional guide torso cage controls are invalid")
    if torso_cage["status"] != "skin-driving torso controls":
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
    section_y: list[float] = []
    for index, (item, (expected_name, expected_role)) in enumerate(zip(sections, expected_sections)):
        if not isinstance(item, dict) or set(item) != {"name", "owner", "center", "lateral_radius", "depth_radius"}:
            raise SurfacePreviewPublishError(f"regional guide torso cage sections[{index}] has an invalid shape")
        if item["name"] != expected_name:
            raise SurfacePreviewPublishError(f"regional guide torso cage sections[{index}] name is invalid")
        section_owner = owner(item["owner"], f"regional-guide.controls.torso_cage.sections[{index}].owner")
        if section_owner["role"] != expected_role or section_owner != parsed_cage_owners[0 if expected_role == "pelvis" else 1]:
            raise SurfacePreviewPublishError(f"regional guide torso cage sections[{index}] owner is invalid")
        center = _point(item["center"], f"regional-guide.controls.torso_cage.sections[{index}].center")
        lateral = _finite_number(item["lateral_radius"], f"regional-guide.controls.torso_cage.sections[{index}].lateral_radius")
        depth = _finite_number(item["depth_radius"], f"regional-guide.controls.torso_cage.sections[{index}].depth_radius")
        if lateral <= 0.0 or depth <= 0.0:
            raise SurfacePreviewPublishError(f"regional guide torso cage sections[{index}] radii must be positive")
        if center[0] - lateral < lower[0] or center[0] + lateral > upper[0] or center[2] - depth < lower[2] or center[2] + depth > upper[2] or center[1] < lower[1] or center[1] > upper[1]:
            raise SurfacePreviewPublishError(f"regional guide torso cage sections[{index}] extend outside shared render bounds")
        section_y.append(center[1])
    if any(section_y[index] >= section_y[index + 1] for index in range(len(section_y) - 1)):
        raise SurfacePreviewPublishError("regional guide torso cage sections are not ordered from pelvis to shoulders")
    connections = torso_cage["connections"]
    expected_connections = [{"from": expected_sections[index][0], "to": expected_sections[index + 1][0]} for index in range(len(expected_sections) - 1)]
    if connections != expected_connections:
        raise SurfacePreviewPublishError("regional guide torso cage connections are invalid")

    shoulder = controls["shoulder_frame"]
    if not isinstance(shoulder, dict) or set(shoulder) != {"status", "owners", "central", "sides"} or shoulder["status"] != "private shoulder frame; support curves guide-only; deltoid sweep skin-driving":
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
    sides = shoulder["sides"]
    if not isinstance(sides, list) or len(sides) != 2 or [item.get("side") for item in sides if isinstance(item, dict)] != ["left", "right"]:
        raise SurfacePreviewPublishError("regional guide shoulder frame sides are invalid")
    for index, side in enumerate(sides):
        where = f"regional-guide.controls.shoulder_frame.sides[{index}]"
        if not isinstance(side, dict) or set(side) != {"side", "owner", "socket", "extremum", "span", "slope", "curves"}:
            raise SurfacePreviewPublishError(f"{where} has an invalid shape")
        side_owner = owner(side["owner"], f"{where}.owner")
        expected_owner = parsed_shoulder_owners[f"{side['side']}_upper_arm"]
        if side_owner != expected_owner:
            raise SurfacePreviewPublishError(f"{where}.owner is invalid")
        for control_name in ("socket", "extremum"):
            control = side[control_name]
            if not isinstance(control, dict) or set(control) != {"owner", "point"} or owner(control["owner"], f"{where}.{control_name}.owner") != side_owner:
                raise SurfacePreviewPublishError(f"{where}.{control_name} is invalid")
            _point(control["point"], f"{where}.{control_name}.point")
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

    head = controls["head"]
    if not isinstance(head, dict) or set(head) != {"owners", "masses", "sections"}:
        raise SurfacePreviewPublishError("regional guide head controls are invalid")
    head_owners = head["owners"]
    if not isinstance(head_owners, list) or len(head_owners) != 2:
        raise SurfacePreviewPublishError("regional guide head owners are invalid")
    parsed_head_owners = [owner(value, f"regional-guide.controls.head.owners[{index}]") for index, value in enumerate(head_owners)]
    if len({json.dumps(value, sort_keys=True) for value in parsed_head_owners}) != 2 or {value["role"] for value in parsed_head_owners} != {"head", "neck"}:
        raise SurfacePreviewPublishError("regional guide head owners are invalid")
    _mass_list(head["masses"], "regional-guide.controls.head.masses", lower, upper, {"cranium", "muzzle", "neck-collar"})
    _path_list(head["sections"], "regional-guide.controls.head.sections", lower, upper, {"head-transition", "neck-transition"})

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
    def close_point(actual: list[float], expected: list[float], where: str) -> None:
        if len(actual) != 3 or len(expected) != 3 or any(not math.isclose(float(a), float(b), rel_tol=1.0e-9, abs_tol=1.0e-12) for a, b in zip(actual, expected)):
            raise SurfacePreviewPublishError(f"{where} does not bind its expected point")

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
        upper_arm = upper_arms.get((side_name,))
        if upper_arm is None:
            raise SurfacePreviewPublishError(f"{where} has no matching upper-arm guide")
        first_section = {section["control"]: section for section in upper_arm["sections"]}.get("pre-joint")
        if first_section is None:
            raise SurfacePreviewPublishError(f"{where} upper-arm guide has no pre-joint section")
        socket = side["socket"]["point"]
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
            if not isinstance(chain, dict) or set(chain) != {"hock", "metatarsal", "masses", "contact_height", "axes"}:
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
    if normalized_owners != descriptor_addresses:
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
        raise SurfacePreviewPublishError("regional guide framing is not the fixed v2 layout")
    _validate_controls(guide.get("controls"), normalized_owners, lower, upper)
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
        raise SurfacePreviewPublishError("surface bundle source_format must be provisional-form v5")
    source = manifest.get("source")
    if not isinstance(source, dict) or set(source) != {"format", "sha256", "document", "namespace", "resource_profile_id", "reference_scale"}:
        raise SurfacePreviewPublishError("surface bundle source must identify format and sha256")
    if source.get("format") != common.PROVISIONAL_FORM_FORMAT or source.get("sha256") != expected_source_sha256:
        raise SurfacePreviewPublishError("surface bundle source does not match the exact v5 producer output")
    source_hash = source.get("sha256")
    if not isinstance(source_hash, str) or len(source_hash) != 64 or any(character not in "0123456789abcdef" for character in source_hash):
        raise SurfacePreviewPublishError("surface bundle source.sha256 is invalid")
    if not all(isinstance(source.get(key), str) and source[key] for key in ("document", "namespace", "resource_profile_id")) or source["resource_profile_id"] != common.PROVISIONAL_FORM_RESOURCE_PROFILE:
        raise SurfacePreviewPublishError("surface bundle source provenance is invalid")
    _validate_reference_scale(source.get("reference_scale"), "surface bundle source.reference_scale")
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
        raise SurfacePreviewPublishError("surface bundle framing is not the fixed v2 layout")
    bounds = manifest.get("shared_render_bounds")
    if not isinstance(bounds, dict) or set(bounds) != {"min", "max"}:
        raise SurfacePreviewPublishError("surface bundle shared_render_bounds is invalid")
    lower, upper = bounds["min"], bounds["max"]
    if not isinstance(lower, list) or not isinstance(upper, list) or len(lower) != 3 or len(upper) != 3 or any(type(item) not in {int, float} for item in lower + upper) or any(a >= b for a, b in zip(lower, upper)):
        raise SurfacePreviewPublishError("surface bundle shared_render_bounds is not ordered")
    generator = manifest.get("generator")
    if not isinstance(generator, dict):
        raise SurfacePreviewPublishError("surface bundle generator must be an explicit configuration object")
    required_generator = {"bundle_version", "samples_per_axis", "padding", "smooth_union", "field_primitives", "field_recipes", "ownership", "boundary"}
    if set(generator) != required_generator:
        raise SurfacePreviewPublishError("surface bundle generator has missing or unknown configuration fields")
    if generator.get("bundle_version") != 2:
        raise SurfacePreviewPublishError("surface bundle generator.bundle_version must be 2")
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
    if not isinstance(variants, list) or [v.get("id") for v in variants if isinstance(v, dict)] != list(EXPECTED_VARIANTS):
        raise SurfacePreviewPublishError("surface bundle variants must be the canonical v5 variants in order")
    inventory_paths: set[str] = set()
    published: list[dict[str, Any]] = []
    producer_variants = producer_payload.get("variants") if producer_payload is not None else None
    if producer_payload is not None and (not isinstance(producer_variants, list) or len(producer_variants) != len(variants)):
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
        producer_variant = producer_variants[index] if producer_variants is not None else None
        if producer_variant is not None:
            if not isinstance(producer_variant, dict) or producer_variant.get("id") != variant["id"]:
                raise SurfacePreviewPublishError(f"{where} does not match producer variant")
            expected_descriptor_addresses = [item.get("address") for item in producer_variant.get("descriptors", [])] if isinstance(producer_variant.get("descriptors"), list) else None
            if expected_descriptor_addresses is None or variant.get("descriptor_address_keys") != expected_descriptor_addresses:
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
            raise SurfacePreviewPublishError(f"{where}.inventory is not the canonical v2 order")
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
                raise SurfacePreviewPublishError(f"{entry_where}.path is not the canonical v2 artifact path")
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
                guide_payload = _validate_guide(artifact, entry, variant_id=variant["id"], manifest=manifest, descriptor_addresses=descriptor_addresses)
        if kinds != {"ply", "semantic-sidecar", "metrics", "guide-skin-composite-png", "regional-guide-json"} or image_entry is None or metrics_payload is None or guide_payload is None:
            raise SurfacePreviewPublishError(f"{where}.inventory has wrong artifact kinds")
        if variant.get("metrics") != metrics_payload:
            raise SurfacePreviewPublishError(f"{where}.metrics does not match the inventoried metrics.json")
        guide_counts = guide_payload["counts"]
        if metrics_payload.get("generated_field_count") != guide_counts["compiled_fields"]:
            raise SurfacePreviewPublishError(f"{where}.metrics.generated_field_count does not match the regional guide")
        if metrics_payload.get("field_recipe_counts") != guide_counts["compiled_field_recipe_counts"]:
            raise SurfacePreviewPublishError(f"{where}.metrics.field_recipe_counts do not match the regional guide")
        if metrics_payload.get("generated_field_count") != EXPECTED_GUIDE_COUNTS["compiled_fields"] or metrics_payload.get("field_recipe_counts") != EXPECTED_GUIDE_COUNTS["compiled_field_recipe_counts"]:
            raise SurfacePreviewPublishError(f"{where}.metrics recipe inventory does not match the expected guide counts")
        published.append({"id": variant["id"], "entry": image_entry})
    actual_paths, actual_directories = _regular_artifacts(bundle)
    actual_paths -= {MANIFEST_NAME}
    if actual_paths != inventory_paths or actual_directories != set(EXPECTED_VARIANTS):
        raise SurfacePreviewPublishError("surface bundle contains unlisted or missing regular output")
    return published, {"source": {"format": source["format"], "sha256": source_hash}, "generator": generator_config}


SUCCESSOR_EXTREMITY_ORDER = (
    "left-hand-attachment", "left-hand-paw", "left-foot",
    "right-hand-attachment", "right-hand-paw", "right-foot",
)
SUCCESSOR_EXTREMITY_KINDS = (
    "hand-attachment", "hand-paw", "foot-chain",
    "hand-attachment", "hand-paw", "foot-chain",
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


def _validate_successor_sidecar(
    path: Path,
    *,
    variant_id: str,
    profile_id: str,
    source_variant_sha256: str,
    source: dict[str, Any],
    frame: dict[str, Any],
    metrics: dict[str, Any],
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

    capture = sidecar.get("capture")
    if not isinstance(capture, dict) or set(capture) != set(frame) or capture != frame:
        raise SurfacePreviewPublishError("successor sidecar capture framing does not match baseline")

    torso = sidecar.get("torso")
    if not isinstance(torso, dict) or set(torso) != {"representation", "sections_consumed", "section_names"}:
        raise SurfacePreviewPublishError("successor torso representation metadata is missing")
    if torso.get("representation") != "frame-aware-ordered-profile-sweep" or type(torso.get("sections_consumed")) is not int or torso["sections_consumed"] != 7:
        raise SurfacePreviewPublishError("successor torso representation metadata is invalid")
    if not isinstance(torso.get("section_names"), list) or len(torso["section_names"]) != torso["sections_consumed"]:
        raise SurfacePreviewPublishError("successor torso section metadata is invalid")

    shoulders = sidecar.get("shoulders")
    if not isinstance(shoulders, dict) or set(shoulders) != {"representation", "spans_consumed", "curve", "span_index"}:
        raise SurfacePreviewPublishError("successor shoulder representation metadata is missing")
    if (
        shoulders.get("representation") != "distal-deltoid-swept-curve-spans"
        or type(shoulders.get("spans_consumed")) is not int
        or shoulders["spans_consumed"] != 2
        or shoulders.get("curve") != "deltoid-sweep"
        or type(shoulders.get("span_index")) is not int
        or shoulders.get("span_index") != 1
    ):
        raise SurfacePreviewPublishError("successor shoulder representation metadata is invalid")

    head_neck = sidecar.get("head_neck")
    if not isinstance(head_neck, dict) or set(head_neck) != {"representation", "sweeps_consumed", "sweep_order", "section_counts", "owner_keys"}:
        raise SurfacePreviewPublishError("successor head/neck representation metadata is missing")
    if head_neck.get("representation") != "shared-guide-derived-profile-sweeps" or type(head_neck.get("sweeps_consumed")) is not int or head_neck["sweeps_consumed"] != 5:
        raise SurfacePreviewPublishError("successor head/neck representation metadata is invalid")
    if not isinstance(head_neck.get("sweep_order"), list) or len(head_neck["sweep_order"]) != 5 or not isinstance(head_neck.get("section_counts"), list) or len(head_neck["section_counts"]) != 5:
        raise SurfacePreviewPublishError("successor head/neck sweep metadata is invalid")

    limbs = sidecar.get("limbs")
    if not isinstance(limbs, dict) or set(limbs) != {"representation", "sweeps_consumed", "sweep_order", "station_counts", "station_names", "section_owner_keys", "endpoint_cap_counts"}:
        raise SurfacePreviewPublishError("successor limb representation metadata is missing")
    if limbs.get("representation") != "shared-guide-derived-ordered-profile-sweeps" or type(limbs.get("sweeps_consumed")) is not int or limbs["sweeps_consumed"] != 4:
        raise SurfacePreviewPublishError("successor limb representation metadata is invalid")
    for key in ("sweep_order", "station_counts", "station_names", "section_owner_keys", "endpoint_cap_counts"):
        if not isinstance(limbs.get(key), list) or len(limbs[key]) != 4:
            raise SurfacePreviewPublishError(f"successor limb {key} metadata is invalid")

    extremities = sidecar.get("extremities")
    if not isinstance(extremities, dict) or set(extremities) != {
        "representation", "sweeps_consumed", "sweep_order", "sweep_kinds", "station_counts",
        "station_names", "section_owner_keys", "endpoint_cap_counts", "internal_transition_counts",
    }:
        raise SurfacePreviewPublishError("successor extremity representation metadata is missing")
    if extremities.get("representation") != "shared-guide-derived-hand-and-digitigrade-foot-profile-sweeps" or extremities.get("sweeps_consumed") != 6:
        raise SurfacePreviewPublishError("successor extremity sweep count is not six")
    if extremities.get("sweep_order") != list(SUCCESSOR_EXTREMITY_ORDER) or extremities.get("sweep_kinds") != list(SUCCESSOR_EXTREMITY_KINDS):
        raise SurfacePreviewPublishError("successor extremity sweep order or kinds are invalid")
    for key in ("station_counts", "station_names", "section_owner_keys", "endpoint_cap_counts", "internal_transition_counts"):
        if not isinstance(extremities.get(key), list) or len(extremities[key]) != 6:
            raise SurfacePreviewPublishError(f"successor extremity {key} metadata is invalid")

    tail = sidecar.get("tail")
    if not isinstance(tail, dict) or set(tail) != {
        "representation", "elements_consumed", "element_order", "element_kinds", "section_counts",
        "section_names", "owner_keys", "endpoint_cap_counts", "internal_transition_counts",
        "controls", "tip_shared_endpoint",
    }:
        raise SurfacePreviewPublishError("successor tail representation metadata is missing")
    if tail.get("representation") != "shared-guide-derived-profile-sweep-elements" or tail.get("elements_consumed") != 6:
        raise SurfacePreviewPublishError("successor tail element count is not six")
    if tail.get("element_order") != list(SUCCESSOR_TAIL_ORDER) or tail.get("element_kinds") != list(SUCCESSOR_TAIL_KINDS):
        raise SurfacePreviewPublishError("successor tail element order or kinds are invalid")
    for key in ("section_counts", "section_names", "owner_keys", "endpoint_cap_counts", "internal_transition_counts"):
        if not isinstance(tail.get(key), list) or len(tail[key]) != 6:
            raise SurfacePreviewPublishError(f"successor tail {key} metadata is invalid")

    bridge = sidecar.get("temporary_bridge")
    if not isinstance(bridge, dict) or set(bridge) != {"enabled", "consumer", "regions", "field_count", "retained_recipes"}:
        raise SurfacePreviewPublishError("successor temporary bridge metadata is missing")
    if (
        bridge.get("enabled") is not True
        or bridge.get("consumer") != "baseline-analytic-fields"
        or bridge.get("regions") != ["limb-root-connectors", "hip-transitions"]
        or bridge.get("field_count") != 6
        or bridge.get("retained_recipes") != list(SUCCESSOR_RETAINED_BRIDGE_RECIPES)
    ):
        raise SurfacePreviewPublishError("successor temporary bridge must contain only six root/hip fields")
    retained = bridge["retained_recipes"]
    if any(recipe in SUCCESSOR_REPLACED_EXTREMITY_AND_TAIL_RECIPES for recipe in retained):
        raise SurfacePreviewPublishError("successor temporary bridge retains baseline paw, foot, or tail recipes")

    replaced = sidecar.get("replaced_baseline_recipes")
    if not isinstance(replaced, list) or not all(isinstance(recipe, str) and recipe for recipe in replaced):
        raise SurfacePreviewPublishError("successor replaced-baseline recipe metadata is invalid")
    if not SUCCESSOR_REQUIRED_REPLACED_RECIPES <= set(replaced):
        raise SurfacePreviewPublishError("successor sidecar does not claim replacement of baseline deltoid, paw, foot, and tail recipes")
    if any(recipe in SUCCESSOR_REPLACED_EXTREMITY_AND_TAIL_RECIPES for recipe in retained):
        raise SurfacePreviewPublishError("successor sidecar retains a replaced baseline recipe")

    if metrics.get("consumer_id") != SUCCESSOR_CONSUMER_ID or metrics.get("successor_region_id") != SUCCESSOR_REGION_ID:
        raise SurfacePreviewPublishError("successor metrics identity does not match sidecar")
    metrics_region = metrics.get("successor_region")
    if not isinstance(metrics_region, dict) or not metrics_region:
        raise SurfacePreviewPublishError("successor metrics lack region representation metadata")
    if (
        metrics_region.get("shoulder_representation") != "distal-deltoid-swept-curve-spans"
        or type(metrics_region.get("shoulder_spans_consumed")) is not int
        or metrics_region.get("shoulder_spans_consumed") != 2
        or metrics_region.get("shoulder_curve") != "deltoid-sweep"
        or type(metrics_region.get("shoulder_span_index")) is not int
        or metrics_region.get("shoulder_span_index") != 1
        or metrics_region.get("extremity_sweeps_consumed") != 6
        or metrics_region.get("tail_elements_consumed") != 6
    ):
        raise SurfacePreviewPublishError("successor metrics lack truthful shoulder, extremity, and tail claims")
    if metrics_region.get("replaced_baseline_recipes") != replaced or metrics.get("temporary_bridge") != bridge:
        raise SurfacePreviewPublishError("successor metrics disagree with sidecar checkpoint metadata")
    return sidecar


def _validate_successor_bundle(
    bundle: Path,
    expected_source_sha256: str,
    producer_payload: dict[str, Any],
    baseline_manifest: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Validate only the successor v2 publication boundary against baseline v2."""

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
    if not isinstance(generator, dict) or set(generator) != {"samples_per_axis", "padding", "capture_padding", "smooth_k", "consumer_boundary", "production_status"}:
        raise SurfacePreviewPublishError("successor generator configuration has unknown or missing fields")
    _finite_json(generator, "successor generator")
    _bounded_json(generator, "successor generator")
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
    if generator.get("production_status") != "disposable exploratory proof" or not isinstance(generator.get("consumer_boundary"), str) or not generator["consumer_boundary"]:
        raise SurfacePreviewPublishError("successor generator boundary metadata is invalid")

    variants = manifest.get("variants")
    if not isinstance(variants, list) or len(variants) != len(EXPECTED_VARIANTS) or [item.get("id") for item in variants if isinstance(item, dict)] != list(EXPECTED_VARIANTS):
        raise SurfacePreviewPublishError("successor variants must be the canonical four variants in order")
    producer_variants = producer_payload.get("variants")
    if not isinstance(producer_variants, list) or len(producer_variants) != len(EXPECTED_VARIANTS):
        raise SurfacePreviewPublishError("successor variants cannot bind producer raw variants")
    published: list[dict[str, Any]] = []
    inventory_paths: set[str] = set()
    expected_kinds = ["ply", "metrics", "successor-consumer-sidecar", "guide-skin-composite-png"]
    expected_frame = {key: baseline_manifest[key] for key in frame_keys}
    for index, variant in enumerate(variants):
        where = f"successor.variants[{index}]"
        if not isinstance(variant, dict) or set(variant) != {"id", "profile_id", "source_variant_sha256", "metrics", "inventory"}:
            raise SurfacePreviewPublishError(f"{where} has unknown or missing fields")
        variant_id = EXPECTED_VARIANTS[index]
        if variant.get("id") != variant_id or variant.get("profile_id") != variant_id:
            raise SurfacePreviewPublishError(f"{where} has an invalid canonical id or profile")
        expected_variant_sha256 = _source_variant_sha256(producer_variants[index], f"{where}.source_variant_sha256")
        source_variant_sha256 = variant.get("source_variant_sha256")
        if not isinstance(source_variant_sha256, str) or len(source_variant_sha256) != 64 or any(character not in "0123456789abcdef" for character in source_variant_sha256):
            raise SurfacePreviewPublishError(f"{where}.source_variant_sha256 is invalid")
        if source_variant_sha256 != expected_variant_sha256:
            raise SurfacePreviewPublishError(f"{where}.source_variant_sha256 does not match producer output")
        inventory = variant.get("inventory")
        if not isinstance(inventory, list) or len(inventory) != 4 or [item.get("kind") for item in inventory if isinstance(item, dict)] != expected_kinds:
            raise SurfacePreviewPublishError(f"{where}.inventory is not the exact four-artifact order")
        expected_paths = {
            "ply": f"{variant_id}/surface.ply",
            "metrics": f"{variant_id}/metrics.json",
            "successor-consumer-sidecar": f"{variant_id}/successor.json",
            "guide-skin-composite-png": f"{variant_id}/guide-skin-composite.png",
        }
        metrics_payload: dict[str, Any] | None = None
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
            if kind == "guide-skin-composite-png":
                image_entry = entry
                _validate_png(artifact, entry, rel_text)
                if entry["width"] != expected_frame["canvas"]["width"] or entry["height"] != expected_frame["canvas"]["height"] or entry["mode"] != expected_frame["canvas"]["mode"]:
                    raise SurfacePreviewPublishError(f"{entry_where} PNG metadata does not match baseline framing")
            elif kind == "metrics":
                metrics_payload = _read_json(artifact, MAX_METRICS_BYTES, f"{where}.metrics.json")
                _finite_json(metrics_payload, f"{where}.metrics.json")
                _bounded_json(metrics_payload, f"{where}.metrics.json")
            elif kind == "successor-consumer-sidecar":
                sidecar_payload = _validate_successor_sidecar(artifact, variant_id=variant_id, profile_id=variant_id, source_variant_sha256=source_variant_sha256, source=source, frame=expected_frame, metrics=variant["metrics"] if isinstance(variant.get("metrics"), dict) else {})
        if kinds != set(expected_kinds) or metrics_payload is None or sidecar_payload is None or image_entry is None:
            raise SurfacePreviewPublishError(f"{where}.inventory is incomplete")
        if variant.get("metrics") != metrics_payload:
            raise SurfacePreviewPublishError(f"{where}.metrics does not match the inventoried metrics.json")
        if not isinstance(variant.get("metrics"), dict):
            raise SurfacePreviewPublishError(f"{where}.metrics must be an object")
        published.append({"id": variant_id, "entry": image_entry, "metrics": metrics_payload, "sidecar": sidecar_payload})

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
    title: str = "First baseline-versus-successor surface checkpoint",
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
    with tempfile.TemporaryDirectory(prefix="ck-surface-preview-") as temp_name:
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
            raise SurfacePreviewPublishError("creature-kernel inspection did not produce v5")
        producer_output.write_text(canonical_json(payload), encoding="utf-8")
        producer_sha256, _ = _sha256(producer_output, "v5 producer output")
        producer_evidence = _validate_producer_evidence(
            _read_producer_evidence(producer_output), "v5 producer evidence"
        )
        if producer_evidence["producer_v5_sha256"] != producer_sha256:
            raise SurfacePreviewPublishError(
                "v5 producer evidence does not match the consumed producer output"
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
            successor_bundle, producer_sha256, payload, baseline_manifest
        )
        baseline_by_id = {item["id"]: item for item in published_baseline}
        successor_by_id = {item["id"]: item for item in published_successor}
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
                        "description": "Baseline analytic-form composite: front, side, and three-quarter views in the shared capture frame.",
                        "metadata": {
                            "variant_id": variant_id,
                            "source_role": "baseline",
                            "source_format": common.PROVISIONAL_FORM_FORMAT,
                            "source_sha256": producer_sha256,
                            "generator": baseline_metadata["generator"],
                            "views": list(EXPECTED_VIEWS),
                            "panels_per_view": 2,
                        },
                    },
                    {
                        "id": f"{variant_id}-successor",
                        "title": f"{title_prefix} — successor",
                        "source": str(successor_bundle / successor_item["entry"]["path"]),
                        "description": "Successor profile-sweep composite: front, side, and three-quarter views in the same shared capture frame.",
                        "metadata": {
                            "variant_id": variant_id,
                            "source_role": "successor",
                            "source_format": SUCCESSOR_PREVIEW_FORMAT,
                            "source_sha256": producer_sha256,
                            "consumer_id": SUCCESSOR_CONSUMER_ID,
                            "successor_region_id": SUCCESSOR_REGION_ID,
                            "generator": successor_metadata["generator"],
                            "views": list(EXPECTED_VIEWS),
                            "panels_per_view": 2,
                        },
                    },
                ],
            })
        descriptor_snapshot = _validate_input_evidence({
            "source_format": common.PROVISIONAL_FORM_FORMAT,
            "source_sha256": producer_sha256,
            "variants": list(EXPECTED_VARIANTS),
            "images": 8,
            **input_evidence,
            **producer_evidence,
        }, "review.subject_context.descriptor_snapshot")
        _validate_producer_evidence(
            descriptor_snapshot, "review.subject_context.descriptor_snapshot"
        )
        if descriptor_snapshot["producer_v5_sha256"] != descriptor_snapshot["source_sha256"]:
            raise SurfacePreviewPublishError(
                "review lineage does not bind the consumed v5 producer output"
            )
        manifest_path.write_text(canonical_json({
            "schema_version": 1,
            "id": stable_id,
            "title": title,
            "description": "First disposable baseline-versus-successor visual checkpoint using one source and one shared capture frame; not production geometry or acceptance evidence.",
            "instructions": "For each variant, compare baseline first and successor second. Appraise overall creature coherence and recognizability, connected joints/extremities/tail, silhouette, and meaningful differentiation between variants. This gallery records no acceptance decision.",
            "subject_context": {
                "authored_summary": {"text": "This is the first baseline-versus-successor visual checkpoint: the same source and shared front/side/three-quarter framing are shown as four ordered pairs. Ben should appraise overall creature coherence and recognizability, connected joints/extremities/tail, silhouette, and meaningful variant differentiation."},
                "descriptor_snapshot": descriptor_snapshot,
                "provenance": {"producer": "inspect-provisional-form", "baseline_generator_script": generator_path.name, "successor_generator_script": successor_generator_path.name, "baseline_generator": baseline_metadata["generator"], "successor_generator": successor_metadata["generator"], "capture": "same source and framing", "limitations": "Disposable, non-production visual checkpoint only; no acceptance, runtime, or Readiness 3 claim."},
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
    parser.add_argument("--title", default="First baseline-versus-successor surface checkpoint")
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

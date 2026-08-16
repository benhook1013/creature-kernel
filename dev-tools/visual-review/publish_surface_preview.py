#!/usr/bin/env python3
"""Publish a disposable experiment surface preview through the image gallery.

This is deliberately an adapter, not a surface renderer.  It runs the current
v4 filled-form producer and an explicitly selected experiment generator in
isolated temporary storage, then publishes only the generator's four PNG
composites into the existing immutable image-review format.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import selectors
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
from publish import PublishError, publish_session
from publish_provisional_form import (
    _copy_input_reference,
    _parse_inspection,
    _validate_input,
)


class SurfacePreviewPublishError(RuntimeError):
    """A bounded, user-facing publication failure."""


SURFACE_PREVIEW_FORMAT = "creature-kernel.disposable-surface-preview.v1"
EXPECTED_VARIANTS = common.PROVISIONAL_FORM_VARIANT_IDS
EXPECTED_VIEWS = ("front", "side", "three-quarter")
MANIFEST_NAME = "surface-preview-manifest.json"
MAX_STDOUT_BYTES = common.MAX_STRUCTURE_JSON_BYTES
MAX_STDERR_BYTES = 64 * 1024
MAX_MANIFEST_BYTES = 256 * 1024
MAX_ARTIFACT_BYTES = 16 * 1024 * 1024
MAX_PNG_WIDTH = 4096
MAX_PNG_HEIGHT = 4096
MAX_PNG_DECODED_BYTES = MAX_PNG_WIDTH * MAX_PNG_HEIGHT * 4 + MAX_PNG_HEIGHT
READ_CHUNK = 64 * 1024
INSPECTION_TIMEOUT_SECONDS = 10.0
GENERATOR_TIMEOUT_SECONDS = 120.0
PROCESS_GRACE_SECONDS = 0.5


def default_creature_kernel() -> Path:
    return Path(__file__).resolve().parents[2] / "target" / "debug" / "creature-kernel"


def default_generator() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "experiments"
        / "current-form-surface-preview"
        / "generate_surface_preview.py"
    )


def _stop_process(process: subprocess.Popen[bytes]) -> None:
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGTERM)
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
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGKILL)
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
                _stop_process(process)
                break
            events = selector.select(remaining)
            if not events:
                failure = SurfacePreviewPublishError(f"{label} timed out after {timeout:g}s")
                _stop_process(process)
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
                    _stop_process(process)
                    break
                buffer.extend(chunk)
            if failure is not None:
                break
        if failure is not None:
            raise failure
        try:
            returncode = process.wait(timeout=PROCESS_GRACE_SECONDS)
        except subprocess.TimeoutExpired as exc:
            _stop_process(process)
            raise SurfacePreviewPublishError(f"{label} did not exit") from exc
        return bytes(streams[stdout_fd][1]), bytes(streams[stderr_fd][1]), returncode
    finally:
        selector.close()
        for stream, _, _, _ in streams.values():
            try:
                stream.close()
            except OSError:
                pass
        if process.poll() is None:
            _stop_process(process)


def _read_json(path: Path, limit: int, where: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise SurfacePreviewPublishError(f"{where} must be a regular non-symlink file")
    try:
        if path.stat().st_size > limit:
            raise SurfacePreviewPublishError(f"{where} exceeds {limit} bytes")
        value = json.loads(path.read_text(encoding="utf-8"))
    except SurfacePreviewPublishError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
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


def _regular_artifacts(root: Path) -> set[str]:
    found: set[str] = set()
    for current, directories, files in os.walk(root, followlinks=False):
        current_path = Path(current)
        for name in directories + files:
            path = current_path / name
            rel = path.relative_to(root).as_posix()
            if path.is_symlink():
                raise SurfacePreviewPublishError(f"surface bundle contains symlink: {rel}")
            if path.is_file():
                found.add(rel)
            elif not path.is_dir():
                raise SurfacePreviewPublishError(f"surface bundle contains non-regular path: {rel}")
    return found


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
    if entry.get("width") != width or entry.get("height") != height:
        raise SurfacePreviewPublishError(f"{where} dimensions do not match inventory")
    mode = entry.get("mode")
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


def _validate_bundle(bundle: Path, expected_source_sha256: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    try:
        bundle_info = bundle.lstat()
    except OSError as exc:
        raise SurfacePreviewPublishError("surface bundle root is unavailable") from exc
    if stat.S_ISLNK(bundle_info.st_mode) or not stat.S_ISDIR(bundle_info.st_mode):
        raise SurfacePreviewPublishError("surface bundle root must be a real non-symlink directory")
    manifest_path = bundle / MANIFEST_NAME
    manifest = _read_json(manifest_path, MAX_MANIFEST_BYTES, MANIFEST_NAME)
    if manifest.get("format") != SURFACE_PREVIEW_FORMAT or manifest.get("status") != "success":
        raise SurfacePreviewPublishError("surface bundle has unsupported format or status")
    if set(manifest) - {"format", "status", "source_format", "source", "generator", "variants"}:
        raise SurfacePreviewPublishError("surface bundle has unknown manifest fields")
    if manifest.get("source_format") != common.PROVISIONAL_FORM_FORMAT:
        raise SurfacePreviewPublishError("surface bundle source_format must be provisional-form v4")
    source = manifest.get("source")
    if not isinstance(source, dict):
        raise SurfacePreviewPublishError("surface bundle source must identify format and sha256")
    if source.get("format") != common.PROVISIONAL_FORM_FORMAT or source.get("sha256") != expected_source_sha256:
        raise SurfacePreviewPublishError("surface bundle source does not match the exact v4 producer output")
    source_hash = source.get("sha256")
    if not isinstance(source_hash, str) or len(source_hash) != 64:
        raise SurfacePreviewPublishError("surface bundle source.sha256 is invalid")
    generator = manifest.get("generator")
    if not isinstance(generator, dict):
        raise SurfacePreviewPublishError("surface bundle generator must be an explicit configuration object")
    required_generator = {"samples_per_axis", "padding", "smooth_union", "field_primitives", "boundary"}
    if set(generator) != required_generator:
        raise SurfacePreviewPublishError("surface bundle generator has missing or unknown configuration fields")
    if type(generator.get("samples_per_axis")) is not int or not 1 <= generator["samples_per_axis"] <= 128:
        raise SurfacePreviewPublishError("surface bundle generator.samples_per_axis is out of bounds")
    if type(generator.get("padding")) not in {int, float} or not 0 <= generator["padding"] <= 100:
        raise SurfacePreviewPublishError("surface bundle generator.padding is out of bounds")
    field_primitives = generator.get("field_primitives")
    if not isinstance(field_primitives, list) or not field_primitives or len(field_primitives) > 16 or not all(isinstance(item, str) and item for item in field_primitives):
        raise SurfacePreviewPublishError("surface bundle generator.field_primitives is invalid")
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
        raise SurfacePreviewPublishError("surface bundle variants must be the canonical v4 variants in order")
    inventory_paths: set[str] = set()
    published: list[dict[str, Any]] = []
    for index, variant in enumerate(variants):
        where = f"variants[{index}]"
        if not isinstance(variant, dict):
            raise SurfacePreviewPublishError(f"{where} must be an object")
        if variant.get("profile_id") != variant.get("id"):
            raise SurfacePreviewPublishError(f"{where}.profile_id must equal id")
        inventory = variant.get("inventory")
        if not isinstance(inventory, list) or len(inventory) != 4:
            raise SurfacePreviewPublishError(f"{where}.inventory must contain exactly four artifacts")
        kinds: set[str] = set()
        image_entry: dict[str, Any] | None = None
        for entry_index, entry in enumerate(inventory):
            entry_where = f"{where}.inventory[{entry_index}]"
            if not isinstance(entry, dict):
                raise SurfacePreviewPublishError(f"{entry_where} must be an object")
            kind = entry.get("kind")
            if kind not in {"ply", "semantic-sidecar", "metrics", "neutral-composite-png"} or kind in kinds:
                raise SurfacePreviewPublishError(f"{entry_where}.kind is missing or duplicated")
            kinds.add(kind)
            rel = _safe_relative(entry.get("path"), f"{entry_where}.path")
            rel_text = rel.as_posix()
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
            if kind == "neutral-composite-png":
                image_entry = entry
                _validate_png(artifact, entry, rel_text)
        if kinds != {"ply", "semantic-sidecar", "metrics", "neutral-composite-png"} or image_entry is None:
            raise SurfacePreviewPublishError(f"{where}.inventory has wrong artifact kinds")
        published.append({"id": variant["id"], "entry": image_entry})
    actual_paths = _regular_artifacts(bundle) - {MANIFEST_NAME}
    if actual_paths != inventory_paths:
        raise SurfacePreviewPublishError("surface bundle contains unlisted or missing regular output")
    return published, {"source": {"format": source["format"], "sha256": source_hash}, "generator": generator_config}


def publish_surface_preview(
    reviews_root: Path,
    input_path: Path,
    *,
    generator: Path | None = None,
    creature_kernel: Path | None = None,
    review_id: str = "surface-preview",
    title: str = "Disposable continuous-surface preview",
) -> dict[str, Any]:
    """Run producer/generator in temp space and publish four composite images."""

    try:
        stable_id = validate_id(review_id, "review id")
    except ValidationError as exc:
        raise SurfacePreviewPublishError(str(exc)) from exc
    if not isinstance(title, str) or not title.strip() or len(title) > 512:
        raise SurfacePreviewPublishError("review title must be a non-empty string no longer than 512 characters")
    input_source = _validate_input(input_path)
    executable = (creature_kernel or default_creature_kernel()).absolute()
    generator_path = (generator or default_generator()).absolute()
    with tempfile.TemporaryDirectory(prefix="ck-surface-preview-") as temp_name:
        work = Path(temp_name)
        input_copy = work / "input.json"
        producer_output = work / "provisional-form.json"
        bundle = work / "bundle"
        _copy_input_reference(input_source, input_copy)
        stdout, stderr, returncode = _run_bounded(
            [str(executable), "inspect-provisional-form", "--input", str(input_copy)],
            timeout=INSPECTION_TIMEOUT_SECONDS,
            label="creature-kernel inspection",
        )
        if returncode != 0:
            detail = stderr.decode("utf-8", errors="replace").strip()[:240]
            raise SurfacePreviewPublishError(f"creature-kernel inspection failed ({returncode}){': ' + detail if detail else ''}")
        payload = _parse_inspection(stdout)
        if payload.get("format") != common.PROVISIONAL_FORM_FORMAT:
            raise SurfacePreviewPublishError("creature-kernel inspection did not produce v4")
        producer_output.write_text(canonical_json(payload), encoding="utf-8")
        producer_sha256, _ = _sha256(producer_output, "v4 producer output")
        generator_stdout, generator_stderr, generator_returncode = _run_bounded(
            [sys.executable, str(generator_path), "--input", str(producer_output), "--output", str(bundle)],
            timeout=GENERATOR_TIMEOUT_SECONDS,
            label="surface generator",
        )
        if generator_returncode != 0:
            detail = generator_stderr.decode("utf-8", errors="replace").strip()[:240]
            raise SurfacePreviewPublishError(f"surface generator failed ({generator_returncode}){': ' + detail if detail else ''}")
        published, bundle_metadata = _validate_bundle(bundle, producer_sha256)
        manifest_path = work / "review-manifest.json"
        groups = [{
            "id": "profiles",
            "title": "Surface profiles",
            "selection_mode": "none",
            "items": [{
                "id": item["id"],
                "title": item["id"],
                "source": str(bundle / item["entry"]["path"]),
                "description": "Neutral composite showing front, side, and three-quarter views.",
                "metadata": {"source_format": common.PROVISIONAL_FORM_FORMAT, "source_sha256": producer_sha256, "generator": bundle_metadata["generator"], "views": list(EXPECTED_VIEWS)},
            } for item in published],
        }]
        manifest_path.write_text(canonical_json({
            "schema_version": 1,
            "id": stable_id,
            "title": title,
            "description": "Disposable current-source surface generator preview; not production geometry or Readiness 3 evidence.",
            "instructions": "Compare the four generated profile composites. The gallery records no product decision.",
            "subject_context": {
                "authored_summary": {"text": "One generated stylized digitigrade biped profile per card; each card contains front, side, and three-quarter views."},
                "descriptor_snapshot": {"source_format": common.PROVISIONAL_FORM_FORMAT, "source_sha256": producer_sha256, "variants": [item["id"] for item in published]},
                "provenance": {"producer": "inspect-provisional-form", "generator_script": generator_path.name, "generator": bundle_metadata["generator"], "limitations": "Disposable preview only; no production geometry, runtime, or Readiness 3 claim."},
            },
            "groups": groups,
        }), encoding="utf-8")
        try:
            summary = publish_session(reviews_root, manifest_path)
        except (ValidationError, PublishError, OSError) as exc:
            raise SurfacePreviewPublishError(f"could not publish surface preview: {exc}") from exc
    return {**summary, "kind": "surface-preview", "variants": len(published)}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path, help="existing reviews root")
    parser.add_argument("--input", required=True, type=Path, help="body-document JSON input")
    parser.add_argument("--generator", type=Path, default=None, help="experiment generator script")
    parser.add_argument("--creature-kernel", type=Path, default=None, help="creature-kernel executable")
    parser.add_argument("--id", default="surface-preview", dest="review_id")
    parser.add_argument("--title", default="Disposable continuous-surface preview")
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        summary = publish_surface_preview(args.root, args.input, generator=args.generator, creature_kernel=args.creature_kernel, review_id=args.review_id, title=args.title)
    except (SurfacePreviewPublishError, ValidationError, PublishError, OSError) as exc:
        print(f"publish-surface-preview failed: {exc}", file=sys.stderr)
        return 2
    print(canonical_json(summary), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

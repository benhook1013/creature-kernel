#!/usr/bin/env python3
"""Publish one prepared-source CLI inspection as an immutable local review session."""

from __future__ import annotations

import argparse
import json
import os
import re
import selectors
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import common
from common import ValidationError, canonical_json, validate_id
from publish import PublishError, publish_session


class PreparedSourcePublishError(RuntimeError):
    """A bounded, user-facing prepared-source publication failure."""


MAX_STDOUT_BYTES = common.MAX_STRUCTURE_JSON_BYTES
MAX_STDERR_BYTES = 64 * 1024
READ_CHUNK = 64 * 1024
INSPECTION_TIMEOUT_SECONDS = 10.0
_ID_BAD_CHARS = re.compile(r"[^a-z0-9_-]+")


def default_creature_kernel() -> Path:
    return Path(__file__).resolve().parents[2] / "target" / "debug" / "creature-kernel"


def _stop_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        process.terminate()
    except OSError:
        pass
    try:
        process.wait(timeout=0.5)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        process.kill()
    except OSError:
        pass
    try:
        process.wait(timeout=0.5)
    except subprocess.TimeoutExpired:
        pass


def _run_inspection(command: list[str]) -> tuple[bytes, bytes, int]:
    """Run the local executable with bounded output and wall time."""

    try:
        process = subprocess.Popen(
            command,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            close_fds=True,
        )
    except (OSError, ValueError) as exc:
        raise PreparedSourcePublishError(f"cannot execute creature-kernel CLI: {exc}") from exc
    assert process.stdout is not None
    assert process.stderr is not None
    selector = selectors.DefaultSelector()
    stdout_fd = process.stdout.fileno()
    stderr_fd = process.stderr.fileno()
    streams = {
        stdout_fd: (process.stdout, bytearray(), MAX_STDOUT_BYTES, "stdout"),
        stderr_fd: (process.stderr, bytearray(), MAX_STDERR_BYTES, "stderr"),
    }
    for fd, (stream, _, _, _) in streams.items():
        selector.register(stream, selectors.EVENT_READ, fd)
    failure: PreparedSourcePublishError | None = None
    try:
        deadline = time.monotonic() + INSPECTION_TIMEOUT_SECONDS
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                failure = PreparedSourcePublishError(
                    f"creature-kernel inspection timed out after {INSPECTION_TIMEOUT_SECONDS:g}s"
                )
                _stop_process(process)
                break
            events = selector.select(remaining)
            if not events:
                failure = PreparedSourcePublishError(
                    f"creature-kernel inspection timed out after {INSPECTION_TIMEOUT_SECONDS:g}s"
                )
                _stop_process(process)
                break
            for key, _ in events:
                fd = key.data
                stream, buffer, limit, label = streams[fd]
                try:
                    chunk = os.read(fd, READ_CHUNK)
                except OSError as exc:
                    failure = PreparedSourcePublishError(f"could not read CLI {label}: {exc}")
                    _stop_process(process)
                    break
                if not chunk:
                    try:
                        selector.unregister(stream)
                    except (KeyError, ValueError):
                        pass
                    stream.close()
                    continue
                buffer.extend(chunk)
                if len(buffer) > limit:
                    failure = PreparedSourcePublishError(
                        f"creature-kernel {label} exceeded {limit} bytes"
                    )
                    _stop_process(process)
                    break
            if failure is not None:
                break
        if failure is not None:
            raise failure
        try:
            returncode = process.wait(timeout=0.5)
        except subprocess.TimeoutExpired as exc:
            _stop_process(process)
            raise PreparedSourcePublishError("creature-kernel inspection did not exit") from exc
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


def _parse_inspection(stdout: bytes) -> dict[str, Any]:
    if not stdout.strip():
        raise PreparedSourcePublishError("creature-kernel CLI produced no JSON inspection result")
    try:
        value = json.loads(stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise PreparedSourcePublishError(f"creature-kernel CLI produced invalid JSON: {exc}") from exc
    try:
        return common._validate_prepared_source_envelope(value, "inspection output")
    except ValidationError as exc:
        raise PreparedSourcePublishError(f"unsupported inspection envelope: {exc}") from exc


def _validate_input(path: Path) -> Path:
    path = path.absolute()
    if path.is_symlink() or not path.is_file():
        raise PreparedSourcePublishError(
            "--input must be an existing regular file without symlink components"
        )
    common._reject_symlink_components(path, "--input")
    return path


def _default_id(path: Path) -> str:
    slug = _ID_BAD_CHARS.sub("-", path.stem.lower()).strip("-_")
    if not slug:
        slug = "prepared-source-review"
    if not slug[0].isalnum():
        slug = f"review-{slug}"
    return slug[:64].rstrip("-_") or "prepared-source-review"


def _write_owned_json(path: Path, value: Any) -> None:
    encoded = canonical_json(value).encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        try:
            path.unlink()
        except OSError:
            pass
        raise


def publish_prepared_source(
    reviews_root: Path,
    input_path: Path,
    *,
    review_id: str | None = None,
    title: str | None = None,
    creature_kernel: Path | None = None,
) -> dict[str, Any]:
    """Prepare one body document and publish it through the structure session."""

    input_path = _validate_input(input_path)
    stable_id = review_id or _default_id(input_path)
    try:
        stable_id = validate_id(stable_id, "review id")
    except ValidationError as exc:
        raise PreparedSourcePublishError(str(exc)) from exc
    stable_title = title or f"Prepared source: {input_path.stem}"
    if not isinstance(stable_title, str) or not stable_title.strip() or len(stable_title) > 512:
        raise PreparedSourcePublishError(
            "review title must be a non-empty string no longer than 512 characters"
        )
    executable = (creature_kernel or default_creature_kernel()).absolute()
    command = [str(executable), "inspect-prepared-source", "--input", str(input_path)]
    stdout, stderr, returncode = _run_inspection(command)
    payload = _parse_inspection(stdout)
    detail = stderr.decode("utf-8", errors="replace").strip()
    suffix = f": {detail[:512]}" if detail else ""
    status = payload["status"]
    if returncode == 0 and status != "success":
        raise PreparedSourcePublishError(
            f"creature-kernel CLI exited with status 0 but reported {status}{suffix}"
        )
    if returncode != 0 and status == "success":
        raise PreparedSourcePublishError(
            f"creature-kernel CLI exited with status {returncode} after reporting success{suffix}"
        )

    with tempfile.TemporaryDirectory(prefix="ck-prepared-source-review-") as temporary:
        temporary_root = Path(temporary)
        structure_source = temporary_root / "structure.json"
        manifest_path = temporary_root / "manifest.json"
        _write_owned_json(structure_source, payload)
        _write_owned_json(
            manifest_path,
            {
                "schema_version": 1,
                "id": stable_id,
                "title": stable_title,
                "kind": "structure",
                "structure_source": str(structure_source),
            },
        )
        try:
            summary = publish_session(reviews_root, manifest_path)
        except (ValidationError, PublishError, OSError) as exc:
            raise PreparedSourcePublishError(
                f"could not publish prepared-source review: {exc}"
            ) from exc
    return {**summary, "kind": "structure"}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path, help="existing reviews root")
    parser.add_argument("--input", required=True, type=Path, help="body-document JSON input")
    parser.add_argument("--id", dest="review_id", help="stable review/session ID")
    parser.add_argument("--title", help="review title")
    parser.add_argument(
        "--creature-kernel",
        type=Path,
        default=None,
        help="creature-kernel executable (default: repository target/debug/creature-kernel)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        summary = publish_prepared_source(
            args.root,
            args.input,
            review_id=args.review_id,
            title=args.title,
            creature_kernel=args.creature_kernel,
        )
    except (PreparedSourcePublishError, ValidationError, PublishError, OSError) as exc:
        print(f"publish-prepared-source failed: {exc}", file=sys.stderr)
        return 2
    print(canonical_json(summary), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

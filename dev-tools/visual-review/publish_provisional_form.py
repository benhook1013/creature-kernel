#!/usr/bin/env python3
"""Publish one filled-form CLI inspection as an immutable local review session."""

from __future__ import annotations

import argparse
import json
import os
import re
import selectors
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import common
from common import ValidationError, canonical_json, validate_id
from publish import PublishError, publish_session


class ProvisionalFormPublishError(RuntimeError):
    """A bounded, user-facing filled-form publication failure."""


MAX_STDOUT_BYTES = common.MAX_STRUCTURE_JSON_BYTES
MAX_STDERR_BYTES = 64 * 1024
READ_CHUNK = 64 * 1024
INSPECTION_TIMEOUT_SECONDS = 10.0
ORDINARY_SOURCE_BYTES = 65_536
MAX_INPUT_COPY_BYTES = ORDINARY_SOURCE_BYTES + 1
PROCESS_GRACE_SECONDS = 0.5
_ID_BAD_CHARS = re.compile(r"[^a-z0-9_-]+")


def default_creature_kernel() -> Path:
    return Path(__file__).resolve().parents[2] / "target" / "debug" / "creature-kernel"


def _stop_process(process: subprocess.Popen[bytes]) -> None:
    """Terminate the whole dedicated process group within a bounded grace."""

    group_id = process.pid
    if os.name == "posix":
        try:
            os.killpg(group_id, signal.SIGTERM)
        except (OSError, ProcessLookupError):
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
            os.killpg(group_id, signal.SIGKILL)
        except (OSError, ProcessLookupError):
            pass
    try:
        process.kill()
    except OSError:
        pass
    try:
        process.wait(timeout=PROCESS_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        pass


def _run_inspection(command: list[str]) -> tuple[bytes, bytes, int]:
    """Run the local executable with bounded stdout, stderr, and wall time."""

    try:
        process = subprocess.Popen(
            command,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            close_fds=True,
            start_new_session=True,
        )
    except (OSError, ValueError) as exc:
        raise ProvisionalFormPublishError(f"cannot execute creature-kernel CLI: {exc}") from exc
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
    failure: ProvisionalFormPublishError | None = None
    try:
        deadline = time.monotonic() + INSPECTION_TIMEOUT_SECONDS
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                failure = ProvisionalFormPublishError(
                    f"creature-kernel inspection timed out after {INSPECTION_TIMEOUT_SECONDS:g}s"
                )
                _stop_process(process)
                break
            events = selector.select(remaining)
            if not events:
                failure = ProvisionalFormPublishError(
                    f"creature-kernel inspection timed out after {INSPECTION_TIMEOUT_SECONDS:g}s"
                )
                _stop_process(process)
                break
            for key, _ in events:
                fd = key.data
                stream, buffer, limit, label = streams[fd]
                remaining_bytes = limit - len(buffer)
                read_size = min(READ_CHUNK, remaining_bytes + 1)
                try:
                    chunk = os.read(fd, read_size)
                except OSError as exc:
                    failure = ProvisionalFormPublishError(f"could not read CLI {label}: {exc}")
                    _stop_process(process)
                    break
                if not chunk:
                    try:
                        selector.unregister(stream)
                    except (KeyError, ValueError):
                        pass
                    stream.close()
                    continue
                if len(chunk) > remaining_bytes:
                    buffer.extend(chunk[:remaining_bytes])
                    failure = ProvisionalFormPublishError(
                        f"creature-kernel {label} exceeded {limit} bytes"
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
            raise ProvisionalFormPublishError("creature-kernel inspection did not exit") from exc
        _stop_process(process)
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
        raise ProvisionalFormPublishError("creature-kernel CLI produced no JSON inspection result")
    try:
        value = json.loads(
            stdout.decode("utf-8"),
            parse_constant=lambda name: (_ for _ in ()).throw(ValueError(name)),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise ProvisionalFormPublishError(f"creature-kernel CLI produced invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ProvisionalFormPublishError("creature-kernel CLI result must be a JSON object")
    if value.get("status") != "success":
        diagnostics = value.get("diagnostics")
        detail = ""
        if isinstance(diagnostics, list) and diagnostics and isinstance(diagnostics[0], dict):
            detail = str(diagnostics[0].get("message") or diagnostics[0].get("code") or "")
        suffix = f": {detail[:240]}" if detail else ""
        raise ProvisionalFormPublishError(
            f"creature-kernel provisional-form inspection failed ({value.get('status', 'unknown')}){suffix}"
        )
    try:
        return common._validate_provisional_form_envelope(value, "inspection output")
    except ValidationError as exc:
        raise ProvisionalFormPublishError(f"unsupported provisional-form envelope: {exc}") from exc


def _validate_input(path: Path) -> common.SourceReference:
    path = path.absolute()
    try:
        # Use the same descriptor identity contract as immutable session
        # sources. The generic JSON helper intentionally does not constrain
        # extensions, unlike image publication.
        return common._resolve_file_reference(str(path), path, "--input")
    except ValidationError as exc:
        raise ProvisionalFormPublishError(str(exc)) from exc


def _copy_input_reference(source: common.SourceReference, destination: Path) -> None:
    """Copy only the bounded producer input prefix from the validated inode."""

    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(destination, flags, 0o600)
    try:
        with common.open_source_reference(source, "--input") as stream, os.fdopen(fd, "wb") as output:
            fd = -1
            remaining = MAX_INPUT_COPY_BYTES
            while remaining:
                chunk = stream.read(min(READ_CHUNK, remaining))
                if not chunk:
                    break
                output.write(chunk)
                remaining -= len(chunk)
            output.flush()
            os.fsync(output.fileno())
    except (OSError, ValidationError) as exc:
        if fd >= 0:
            os.close(fd)
        try:
            destination.unlink()
        except OSError:
            pass
        raise ProvisionalFormPublishError(f"could not copy --input safely: {exc}") from exc


def _default_id(path: Path) -> str:
    slug = _ID_BAD_CHARS.sub("-", path.stem.lower()).strip("-_")
    if not slug:
        slug = "provisional-form-review"
    return slug[:64].rstrip("-_") or "provisional-form-review"


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


def publish_provisional_form(
    reviews_root: Path,
    input_path: Path,
    *,
    review_id: str | None = None,
    title: str | None = None,
    creature_kernel: Path | None = None,
) -> dict[str, Any]:
    """Inspect one body document and publish only its validated CLI payload."""

    input_source = _validate_input(input_path)
    input_path = input_source.path
    stable_id = review_id or _default_id(input_path)
    try:
        stable_id = validate_id(stable_id, "review id")
    except ValidationError as exc:
        raise ProvisionalFormPublishError(str(exc)) from exc
    stable_title = title or f"Provisional form: {input_path.stem}"
    if not isinstance(stable_title, str) or not stable_title.strip() or len(stable_title) > 512:
        raise ProvisionalFormPublishError(
            "review title must be a non-empty string no longer than 512 characters"
        )
    executable = (creature_kernel or default_creature_kernel()).absolute()

    with tempfile.TemporaryDirectory(prefix="ck-provisional-form-review-") as temporary:
        temporary_root = Path(temporary)
        input_copy = temporary_root / "input.json"
        form_source = temporary_root / "provisional-form.json"
        manifest_path = temporary_root / "manifest.json"
        _copy_input_reference(input_source, input_copy)
        command = [str(executable), "inspect-provisional-form", "--input", str(input_copy)]
        stdout, stderr, returncode = _run_inspection(command)
        payload = _parse_inspection(stdout)
        detail = stderr.decode("utf-8", errors="replace").strip()
        if returncode != 0:
            suffix = f": {detail[:240]}" if detail else ""
            raise ProvisionalFormPublishError(
                f"creature-kernel inspection exited with status {returncode}{suffix}"
            )
        _write_owned_json(form_source, payload)
        _write_owned_json(
            manifest_path,
            {
                "schema_version": 1,
                "id": stable_id,
                "title": stable_title,
                "kind": "provisional-form",
                "provisional_form_source": str(form_source),
            },
        )
        try:
            summary = publish_session(reviews_root, manifest_path)
        except (ValidationError, PublishError, OSError) as exc:
            raise ProvisionalFormPublishError(
                f"could not publish provisional-form review: {exc}"
            ) from exc
    return {**summary, "kind": "provisional-form"}


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
        summary = publish_provisional_form(
            args.root,
            args.input,
            review_id=args.review_id,
            title=args.title,
            creature_kernel=args.creature_kernel,
        )
    except (ProvisionalFormPublishError, ValidationError, PublishError, OSError) as exc:
        print(f"publish-provisional-form failed: {exc}", file=sys.stderr)
        return 2
    print(canonical_json(summary), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

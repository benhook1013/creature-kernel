"""Capture, verify, and run one selected unittest file from captured source.

This is a thin entrypoint over :mod:`runner` capture provenance.  It does not
copy dependencies independently, discover live tests, or claim a hermetic host.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Callable, Mapping

import runner


_TEST_NAME = re.compile(r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*$")


class CapturedTestError(ValueError):
    """Raised when a captured test cannot be resolved or executed safely."""


def _logical_path(value: str) -> str:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or path.suffix != ".py":
        raise CapturedTestError("test file must be a relative Python source path")
    return path.as_posix()


def _captured_path(manifest: Mapping[str, Any], snapshot: Path,
                   logical_path: str) -> Path:
    source = manifest.get("source")
    rows = source.get("files") if isinstance(source, Mapping) else None
    if not isinstance(rows, list):
        raise CapturedTestError("capture manifest has no source file inventory")
    matches = [row for row in rows
               if isinstance(row, Mapping) and row.get("path") == logical_path]
    if len(matches) != 1 or not isinstance(matches[0].get("snapshot_path"), str):
        raise CapturedTestError(
            f"capture manifest does not resolve exactly one {logical_path!r}")
    recorded = Path(str(matches[0]["snapshot_path"]))
    candidate = recorded if recorded.is_absolute() else snapshot / recorded
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(snapshot.resolve(strict=True))
    except (OSError, ValueError) as exc:
        raise CapturedTestError(
            f"captured test path escapes or is unavailable: {candidate}") from exc
    if resolved.is_symlink() or not resolved.is_file():
        raise CapturedTestError(f"captured test is not a regular file: {resolved}")
    return resolved


def _managed_python(manifest: Mapping[str, Any]) -> Path:
    runtime = manifest.get("runtime")
    value = runtime.get("executable") if isinstance(runtime, Mapping) else None
    if not isinstance(value, str):
        raise CapturedTestError("capture manifest has no managed runtime executable")
    path = Path(value)
    if (not path.is_absolute() or not path.is_file()
            or not os.access(path, os.X_OK)):
        raise CapturedTestError(f"managed runtime executable is unavailable: {path}")
    # Preserve the exact recorded invocation path.  Resolving a venv's
    # bin/python symlink can bypass its pyvenv.cfg and site packages.
    return path


def _capture_names(runner_module: Any, logical_test: str) -> list[str]:
    names = list(runner_module.CAPTURE_FILES)
    for required in ("runner.py", "captured_tests.py", logical_test):
        if required not in names:
            names.append(required)
    return names


def run_captured_tests(
        snapshot_value: str | os.PathLike[str], test_file: str,
        test_names: list[str] | tuple[str, ...] = (), *,
        runner_module: Any = runner,
        process_run: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> dict[str, Any]:
    """Capture first, then run only ``test_file`` from its manifest path."""
    snapshot = Path(snapshot_value).resolve()
    logical_test = _logical_path(test_file)
    selected = list(test_names)
    if any(not _TEST_NAME.fullmatch(name) for name in selected):
        raise CapturedTestError("test names must be dotted unittest identifiers")

    manifest = runner_module.prepare(
        snapshot, file_names=_capture_names(runner_module, logical_test))
    captured_test = _captured_path(manifest, snapshot, logical_test)
    manifest_path = snapshot / "manifest.json"
    runner_module.verify(snapshot)
    interpreter = _managed_python(manifest)
    command = [str(interpreter), str(captured_test), *selected, "-v"]
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    invoke = subprocess.run if process_run is None else process_run

    process_error: dict[str, str] | None = None
    completed: subprocess.CompletedProcess[str] | None = None
    try:
        completed = invoke(
            command, cwd=str(captured_test.parent), env=environment,
            text=True, capture_output=True, check=False)
    except Exception as exc:  # The post-test verification still must run.
        process_error = {"type": type(exc).__name__, "message": str(exc)}

    postverify_error: dict[str, str] | None = None
    try:
        runner_module.verify(snapshot)
    except Exception as exc:
        postverify_error = {"type": type(exc).__name__, "message": str(exc)}

    returncode = completed.returncode if completed is not None else None
    status = ("passed" if returncode == 0 and process_error is None
              and postverify_error is None else "failed")
    return {
        "schema": "creature-kernel.connected-leg-assembly-captured-tests.v1",
        "status": status,
        "snapshot_path": str(snapshot),
        "manifest_path": str(manifest_path),
        "captured_test_path": str(captured_test),
        "managed_python": str(interpreter),
        "selected_tests": selected or ["<all tests in captured file>"],
        "command": command,
        "preverify": "passed",
        "test": {
            "returncode": returncode,
            "stdout": completed.stdout if completed is not None else "",
            "stderr": completed.stderr if completed is not None else "",
            "exception": process_error,
        },
        "postverify": "failed" if postverify_error else "passed",
        "postverify_error": postverify_error,
        "limitations": [
            *list(manifest.get("limitations", [])),
            "Only the selected captured test script is launched; its own unittest selector semantics determine methods run.",
            "External frozen dependencies and the managed runtime retain the capture manifest's reuse and host-hermeticity limits.",
        ],
    }


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Capture and run selected connected-leg unittests")
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--test-file", required=True)
    parser.add_argument("--test-name", action="append", default=[])
    args = parser.parse_args(argv)
    try:
        report = run_captured_tests(
            args.snapshot, args.test_file, args.test_name)
    except Exception as exc:
        report = {
            "schema": "creature-kernel.connected-leg-assembly-captured-tests.v1",
            "status": "error",
            "exception": {"type": type(exc).__name__, "message": str(exc)},
        }
    print(json.dumps(report, sort_keys=True, indent=2, allow_nan=False), flush=True)
    return 0 if report.get("status") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(_main())

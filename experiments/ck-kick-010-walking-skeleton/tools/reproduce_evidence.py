#!/usr/bin/env python3
"""Reproduce CK-KICK-010 local evidence in one invocation-owned directory.

This is disposable experiment tooling, not a production command or formal
experiment runner.  It deliberately invokes the public-ish spike entry point
as a child process so the evidence covers ``python -m ck_spike build`` itself.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from typing import Any


EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VALID_FIXTURE = EXPERIMENT_ROOT / "fixtures" / "valid.json"
DEFAULT_INVALID_FIXTURE = EXPERIMENT_ROOT / "fixtures" / "invalid-missing-right-shin.json"
VALID_ARTIFACTS = [
    "diagnostics.json",
    "manifest.json",
    "mesh.ply",
    "resolved_graph.json",
    "semantic_regions.json",
]
INVALID_ARTIFACTS = ["diagnostics.json", "manifest.json"]
RUNS = (
    ("valid-a", "valid", 0),
    ("valid-b", "valid", 0),
    ("invalid-a", "invalid", 2),
    ("invalid-b", "invalid", 2),
)


class ToolError(ValueError):
    """A concise setup or invocation-owned output error."""


def _absolute(path: Path) -> Path:
    """Make path output stable without resolving user-controlled symlinks."""

    return path.expanduser().absolute()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Disposable CK-KICK-010 evidence reproduction helper."
    )
    parser.add_argument(
        "--output-root",
        required=True,
        type=Path,
        help="new directory to own for this invocation (must not already exist)",
    )
    parser.add_argument(
        "--valid-fixture",
        type=Path,
        default=DEFAULT_VALID_FIXTURE,
        help=f"valid fixture (default: {DEFAULT_VALID_FIXTURE})",
    )
    parser.add_argument(
        "--invalid-fixture",
        type=Path,
        default=DEFAULT_INVALID_FIXTURE,
        help=f"invalid fixture (default: {DEFAULT_INVALID_FIXTURE})",
    )
    parser.add_argument(
        "--samples-per-axis",
        type=int,
        default=128,
        help="grid resolution passed to ck_spike (default: 128)",
    )
    parser.add_argument(
        "--padding",
        type=float,
        default=0.10,
        help="padding passed to ck_spike (default: 0.10)",
    )
    parser.add_argument(
        "--smooth-min-k",
        type=float,
        default=0.10,
        help="smooth-min k passed to ck_spike (default: 0.10)",
    )
    return parser


def _prepare_output_root(output_root: Path, fixtures: tuple[Path, Path]) -> None:
    # lexists also rejects a dangling symlink: following or replacing one
    # would violate the tool's no-overwrite promise.
    if os.path.lexists(output_root):
        raise ToolError(f"output root already exists: {output_root}")
    parent = output_root.parent
    if not parent.exists():
        raise ToolError(f"output root parent does not exist: {parent}")
    if not parent.is_dir():
        raise ToolError(f"output root parent is not a directory: {parent}")
    for fixture in fixtures:
        if not fixture.exists():
            raise ToolError(f"fixture does not exist: {fixture}")
        if not fixture.is_file():
            raise ToolError(f"fixture is not a regular file: {fixture}")
    try:
        output_root.mkdir()
    except FileExistsError as error:
        raise ToolError(f"output root already exists: {output_root}") from error
    except OSError as error:
        raise ToolError(f"could not create output root: {output_root}") from error


def _inventory_and_hashes(directory: Path) -> tuple[list[str], dict[str, str]]:
    """Inventory without following links, and hash regular files only."""

    if not directory.is_dir() or directory.is_symlink():
        return [], {}
    names: list[str] = []
    hashes: dict[str, str] = {}
    pending = [(directory, "")]
    while pending:
        current, prefix = pending.pop()
        try:
            entries = sorted(os.scandir(current), key=lambda entry: entry.name)
        except OSError:
            names.append(prefix + "<unreadable>")
            continue
        for entry in entries:
            relative = f"{prefix}{entry.name}"
            try:
                mode = entry.stat(follow_symlinks=False).st_mode
            except OSError:
                names.append(relative + "\x00")
                continue
            if stat.S_ISREG(mode):
                names.append(relative)
                try:
                    digest = hashlib.sha256()
                    with open(entry.path, "rb", buffering=0) as stream:
                        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                            digest.update(chunk)
                    hashes[relative] = digest.hexdigest()
                except OSError:
                    # Retain the inventory but omit an unreadable file's hash.
                    pass
            elif stat.S_ISDIR(mode):
                names.append(relative + "/")
                pending.append((Path(entry.path), relative + "/"))
            else:
                # This includes symlinks and prevents reading through them.
                names.append(relative + "\x00")
    return sorted(names), {name: hashes[name] for name in sorted(hashes)}


def _byte_equal(first: Path, second: Path, names: list[str]) -> bool:
    if not names:
        return False
    for name in names:
        if name.endswith("/") or "\x00" in name:
            return False
        try:
            if (first / name).read_bytes() != (second / name).read_bytes():
                return False
        except OSError:
            return False
    return True


def _run_build(
    *,
    name: str,
    fixture: Path,
    output: Path,
    samples_per_axis: int,
    padding: float,
    smooth_min_k: float,
) -> dict[str, Any]:
    command = [
        sys.executable,
        "-m",
        "ck_spike",
        "build",
        "--input",
        str(fixture),
        "--output",
        str(output),
        "--samples-per-axis",
        str(samples_per_axis),
        "--padding",
        str(padding),
        "--smooth-min-k",
        str(smooth_min_k),
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=EXPERIMENT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        exit_code: int | None = completed.returncode
        child_error = "" if completed.returncode in (0, 2) else "child command failed"
    except OSError:
        exit_code = None
        child_error = "could not start child command"
    inventory, hashes = _inventory_and_hashes(output)
    return {
        "name": name,
        "input": str(fixture),
        "output": str(output),
        "exit_code": exit_code,
        "inventory": inventory,
        "sha256": hashes,
        "error": child_error,
    }


def _summary(
    *,
    output_root: Path,
    valid_fixture: Path,
    invalid_fixture: Path,
    runs: list[dict[str, Any]],
) -> dict[str, Any]:
    by_name = {run["name"]: run for run in runs}
    comparisons: dict[str, dict[str, Any]] = {}
    for label, first_name, second_name in (
        ("valid", "valid-a", "valid-b"),
        ("invalid", "invalid-a", "invalid-b"),
    ):
        first = by_name[first_name]
        second = by_name[second_name]
        inventory_equal = first["inventory"] == second["inventory"]
        names = first["inventory"] if inventory_equal else []
        comparisons[label] = {
            "runs": [first_name, second_name],
            "inventory_equal": inventory_equal,
            "byte_equal": _byte_equal(
                Path(first["output"]), Path(second["output"]), names
            ),
        }
    return {
        "tool": "ck-kick-010-disposable-evidence-reproduction-v1",
        "output_root": str(output_root),
        "fixtures": {"valid": str(valid_fixture), "invalid": str(invalid_fixture)},
        "runs": runs,
        "comparisons": comparisons,
    }


def reproduce(args: argparse.Namespace) -> tuple[dict[str, Any], list[str]]:
    output_root = _absolute(args.output_root)
    valid_fixture = _absolute(args.valid_fixture)
    invalid_fixture = _absolute(args.invalid_fixture)
    _prepare_output_root(output_root, (valid_fixture, invalid_fixture))

    runs: list[dict[str, Any]] = []
    errors: list[str] = []
    fixtures = {"valid": valid_fixture, "invalid": invalid_fixture}
    expected_inventories = {"valid": VALID_ARTIFACTS, "invalid": INVALID_ARTIFACTS}
    for name, status, expected_code in RUNS:
        run = _run_build(
            name=name,
            fixture=fixtures[status],
            output=output_root / name,
            samples_per_axis=args.samples_per_axis,
            padding=args.padding,
            smooth_min_k=args.smooth_min_k,
        )
        runs.append(run)
        if run["exit_code"] != expected_code:
            errors.append(
                f"{name} exited {run['exit_code']!r}; expected {expected_code}"
            )
        if run["inventory"] != expected_inventories[status]:
            errors.append(f"{name} inventory does not match expected {status} bundle")
        if run["error"]:
            errors.append(f"{name}: {run['error']}")

    result = _summary(
        output_root=output_root,
        valid_fixture=valid_fixture,
        invalid_fixture=invalid_fixture,
        runs=runs,
    )
    for label, comparison in result["comparisons"].items():
        if not comparison["inventory_equal"] or not comparison["byte_equal"]:
            errors.append(f"{label} repeat pair is not byte-identical")
    return result, errors


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        result, errors = reproduce(args)
    except ToolError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    except (OSError, ValueError, TypeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    if errors:
        print("error: " + "; ".join(errors), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

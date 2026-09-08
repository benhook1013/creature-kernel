#!/usr/bin/env python3
"""Preserve the failed hip pre-filter evidence and snapshot its inputs.

This tool deliberately does not import or execute experiment geometry code.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import site
import shutil
import stat
import subprocess
import sys
from typing import Iterable


TRIAL_ROOT = Path("/tmp/ck-hip-prefilter-trial-20260905-a")
PRESERVE_ROOT = Path(
    "/home/ben/.cache/creature-kernel/pelvis-thigh-transition/failed-prefilter-20260905"
)

# These are source/input support areas, not an instruction to capture their
# generated output.  The suffix and excluded-directory rules are intentional
# so a snapshot stays small and reviewable.
DIRECTORY_RULES = (
    ("experiments/pelvis-thigh-transition", (".py", ".json", ".md", ".sh")),
    ("experiments/owned-root-assembly-successor", (".py", ".sh", ".md", ".sha256")),
    ("experiments/owned-root-assembly-successor-exact-five", (".py", ".sh", ".md", ".sha256")),
    ("experiments/programmatic-root-complex-surface", (".py", ".sh", ".md", ".json")),
    ("examples/body-documents", (".json",)),
)
EXPLICIT_FILES = (
    "experiments/current-form-surface-preview/requirements.txt",
    "experiments/current-form-surface-preview/structural_profile_candidates.json",
    "experiments/current-form-surface-preview/surface_preview_launcher.sh",
    "experiments/current-form-surface-preview/generate_structural_profile_sources.py",
    "experiments/current-form-surface-preview/structural_atomic_publish.py",
)
EXCLUDED_PARTS = {
    "__pycache__",
    "results",
    "generated",
    "images",
    "captures",
    "cache",
    ".git",
}
COMPILED_IMPORTS = (
    "numpy",
    "scipy",
    "skimage",
    "PIL",
    "imageio",
    "networkx",
    "tifffile",
)


def fail(message: str) -> "NoReturn":
    raise SystemExit(f"preserve_evidence.py: error: {message}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def regular_file(path: Path) -> None:
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode):
        fail(f"symlink is not allowed: {path}")
    if not stat.S_ISREG(info.st_mode):
        fail(f"non-regular file is not allowed: {path}")


def fresh_directory(path: Path) -> None:
    if not path.is_absolute():
        fail(f"output must be an absolute path: {path}")
    if os.path.lexists(path):
        fail(f"output must be fresh and absent: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.mkdir()


def inventory(root: Path, paths: Iterable[Path]) -> list[dict[str, object]]:
    rows = []
    for path in sorted(paths, key=lambda item: item.as_posix().encode()):
        regular_file(path)
        rows.append(
            {
                "path": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return rows


def trial_files() -> list[Path]:
    if not TRIAL_ROOT.is_dir() or TRIAL_ROOT.is_symlink():
        fail(f"exact original trial directory is unavailable: {TRIAL_ROOT}")
    found = []
    for path in sorted(TRIAL_ROOT.rglob("*"), key=lambda item: item.as_posix().encode()):
        if path.is_symlink():
            fail(f"trial corpus contains a symlink: {path}")
        if path.is_file():
            regular_file(path)
            found.append(path)
    return found


def source_files(root: Path) -> list[Path]:
    selected: set[Path] = set()
    for relative, suffixes in DIRECTORY_RULES:
        directory = root / relative
        if not directory.is_dir() or directory.is_symlink():
            fail(f"allowlisted source directory is unavailable: {directory}")
        for path in directory.rglob("*"):
            relative_to_directory = path.relative_to(directory)
            if any(part in EXCLUDED_PARTS for part in relative_to_directory.parts):
                continue
            if path.is_symlink():
                fail(f"allowlisted source tree contains a symlink: {path}")
            if path.is_file() and path.suffix in suffixes:
                regular_file(path)
                selected.add(path)
    for relative in EXPLICIT_FILES:
        path = root / relative
        if not path.is_file() or path.is_symlink():
            fail(f"allowlisted source file is unavailable or is a symlink: {path}")
        regular_file(path)
        selected.add(path)
    return sorted(selected, key=lambda item: item.relative_to(root).as_posix().encode())


def copy_files(root: Path, files: list[Path], destination: Path) -> list[dict[str, object]]:
    before = inventory(root, files)
    for path, row in zip(files, before):
        relative = path.relative_to(root)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        regular_file(target)
        copied_bytes = target.stat().st_size
        copied_sha256 = sha256_file(target)
        if copied_bytes != row["bytes"] or copied_sha256 != row["sha256"]:
            fail(f"copied bytes differ from source-before inventory: {target}")
    after = inventory(root, files)
    if before != after:
        fail("source changed while being copied; discard this output and retry")
    copied = []
    for row in before:
        target = destination / str(row["path"])
        copied.append({**row, "snapshot_path": target.relative_to(destination.parent).as_posix()})
    return copied


def directory_files(directory: Path) -> list[Path]:
    if not directory.is_dir() or directory.is_symlink():
        fail(f"runtime directory is unavailable or is a symlink: {directory}")
    files = []
    for path in sorted(directory.rglob("*"), key=lambda item: item.relative_to(directory).as_posix().encode()):
        if path.is_symlink():
            fail(f"runtime tree contains a symlink: {path}")
        if path.is_file():
            regular_file(path)
            files.append(path)
    return files


def inventory_digest(rows: list[dict[str, object]]) -> str:
    encoded = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def copy_one_checked(source: Path, target: Path) -> dict[str, object]:
    regular_file(source)
    source_before = {
        "bytes": source.stat().st_size,
        "sha256": sha256_file(source),
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    shutil.copymode(source, target)
    regular_file(target)
    target_after = {
        "bytes": target.stat().st_size,
        "sha256": sha256_file(target),
    }
    if target_after != source_before:
        fail(f"copied runtime bytes differ from source-before identity: {target}")
    source_after = {
        "bytes": source.stat().st_size,
        "sha256": sha256_file(source),
    }
    if source_after != source_before:
        fail(f"runtime source changed while being copied: {source}")
    return {
        "source_path": str(source),
        "bytes": source_before["bytes"],
        "sha256": source_before["sha256"],
        "runtime_sha256": target_after["sha256"],
    }


def copy_runtime_tree(
    source: Path, target: Path, runtime_root: Path
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    source_files = directory_files(source)
    before = inventory(source, source_files)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target, symlinks=False)
    target_files = directory_files(target)
    copied = inventory(target, target_files)
    expected = before
    if copied != expected:
        fail(f"copied runtime tree differs from source-before inventory: {target}")
    after = inventory(source, source_files)
    if before != after:
        fail(f"runtime package source changed while being copied: {source}")
    runtime_rows = []
    for row in before:
        runtime_path = (target / str(row["path"])).relative_to(runtime_root).as_posix()
        runtime_rows.append(
            {
                "path": runtime_path,
                "source_path": str(source / str(row["path"])),
                "bytes": row["bytes"],
                "sha256": row["sha256"],
                "runtime_sha256": row["sha256"],
            }
        )
    return runtime_rows, before, after


def runtime_site_packages(prefix: Path) -> Path:
    candidates = []
    for candidate in site.getsitepackages():
        path = Path(candidate)
        try:
            path.relative_to(prefix)
        except ValueError:
            continue
        if path.is_dir() and not path.is_symlink():
            candidates.append(path)
    if len(candidates) != 1:
        fail(f"expected exactly one in-venv site-packages directory, found: {candidates}")
    return candidates[0]


def clone_runtime(destination: Path) -> dict[str, object]:
    if sys.prefix == sys.base_prefix:
        fail("snapshot requires a virtual environment; sys.prefix equals sys.base_prefix")
    prefix = Path(sys.prefix).resolve()
    executable = Path(sys.executable).resolve()
    base_executable = Path(getattr(sys, "_base_executable", sys.executable)).resolve()
    pyvenv = prefix / "pyvenv.cfg"
    site_packages = runtime_site_packages(prefix)
    regular_file(executable)
    regular_file(base_executable)
    regular_file(pyvenv)

    if destination.exists() or destination.is_symlink():
        fail(f"runtime clone destination must be absent: {destination}")
    destination.mkdir(parents=True)
    runtime_rows = []
    executable_row = copy_one_checked(executable, destination / "bin" / "python")
    executable_row["path"] = "bin/python"
    runtime_rows.append(executable_row)
    pyvenv_row = copy_one_checked(pyvenv, destination / "pyvenv.cfg")
    pyvenv_row["path"] = "pyvenv.cfg"
    runtime_rows.append(pyvenv_row)

    package_target = destination / site_packages.relative_to(prefix)
    package_rows, package_before, package_after = copy_runtime_tree(
        site_packages, package_target, destination
    )
    runtime_rows.extend(package_rows)
    return {
        "clone_root": str(destination),
        "executable": str(destination / "bin" / "python"),
        "source_prefix": str(prefix),
        "source_executable": str(executable),
        "source_executable_sha256": sha256_file(executable),
        "base_prefix": sys.base_prefix,
        "base_executable": str(base_executable),
        "base_executable_sha256": sha256_file(base_executable),
        "platform": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "python_implementation": platform.python_implementation(),
            "python_version": platform.python_version(),
        },
        "site_packages": str(site_packages),
        "source_packages_before": {
            "files": package_before,
            "inventory_sha256": inventory_digest(package_before),
        },
        "source_packages_after": {
            "files": package_after,
            "inventory_sha256": inventory_digest(package_after),
        },
        "files": sorted(runtime_rows, key=lambda row: str(row["path"]).encode()),
        "candidate_environment": {
            "variable": "CK_CURRENT_FORM_SURFACE_PYTHON",
            "value": str(destination / "bin" / "python"),
        },
    }


def package_versions() -> dict[str, str | None]:
    names = (
        "imageio",
        "lazy-loader",
        "networkx",
        "numpy",
        "packaging",
        "Pillow",
        "scikit-image",
        "scipy",
        "tifffile",
    )
    result: dict[str, str | None] = {}
    for name in names:
        try:
            result[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result[name] = None
    return result


def environment_snapshot() -> dict[str, object]:
    freeze = subprocess.run(
        [sys.executable, "-m", "pip", "freeze"],
        check=False,
        capture_output=True,
        text=True,
    )
    loaded_errors = {}
    for name in COMPILED_IMPORTS:
        try:
            importlib.import_module(name)
        except Exception as exc:  # An inventory should remain useful if optional deps are absent.
            loaded_errors[name] = f"{type(exc).__name__}: {exc}"

    extensions = []
    for module_name, module in sorted(sys.modules.items()):
        origin = getattr(module, "__file__", None)
        if not origin or not origin.endswith((".so", ".so.1", ".pyd", ".dylib")):
            continue
        path = Path(origin)
        row: dict[str, object] = {"module": module_name, "path": str(path)}
        if path.is_file() and not path.is_symlink():
            row["bytes"] = path.stat().st_size
            row["sha256"] = sha256_file(path)
        else:
            row["hash_unavailable"] = True
        extensions.append(row)
    return {
        "python_executable": sys.executable,
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "sys_prefix": sys.prefix,
        "package_versions": package_versions(),
        "pip_freeze_returncode": freeze.returncode,
        "pip_freeze": freeze.stdout.splitlines(),
        "pip_freeze_stderr": freeze.stderr.splitlines(),
        "pip_freeze_sha256": hashlib.sha256(freeze.stdout.encode()).hexdigest(),
        "loaded_compiled_extensions": extensions,
        "compiled_import_errors": loaded_errors,
    }


def write_json(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def preserve(output: Path) -> None:
    if output != PRESERVE_ROOT:
        fail(f"preservation output must be the exact requested cache path: {PRESERVE_ROOT}")
    fresh_directory(output)
    raw_paths = trial_files()
    raw_rows = inventory(TRIAL_ROOT, raw_paths)
    raw_destination = output / "original-trial"
    raw_rows = copy_files(TRIAL_ROOT, raw_paths, raw_destination)

    root = Path.cwd().resolve()
    source_paths = source_files(root)
    recovery_destination = output / "recovery" / "source"
    recovery_rows = copy_files(root, source_paths, recovery_destination)
    environment = environment_snapshot()
    write_json(output / "recovery" / "environment.json", environment)

    final = next((row for row in raw_rows if row["path"] == "final-diagnostics2.json"), None)
    render_suffixes = {".png", ".jpg", ".jpeg", ".webp", ".svg"}
    render_files = [row["path"] for row in raw_rows if Path(str(row["path"])).suffix.lower() in render_suffixes]
    manifest = {
        "schema": "pelvis-thigh-transition-failed-prefilter-preservation.v1",
        "status": "preserved",
        "preserved_at": "2026-09-05",
        "original_trial_root": str(TRIAL_ROOT),
        "raw_retained_location": str(raw_destination),
        "raw_files": raw_rows,
        "final_diagnostics2": final,
        "recovery_snapshot": {
            "label": "RECOVERY",
            "not_original_executing_snapshot": True,
            "repository_root": str(root),
            "location": str(recovery_destination),
            "files": recovery_rows,
            "environment_location": str(output / "recovery" / "environment.json"),
        },
        "known_limits": {
            "original_concurrent_edits": "The trial probe imported mutable worktree files by absolute path; no immutable executing-source snapshot was captured. Current source copies are recovery snapshots only.",
            "missing_import_snapshots": "The original run did not retain a module/import snapshot. This preservation records current package/runtime data and best-effort loaded extension hashes, not the original import state.",
            "trial_surface_renders": "No surface-render files were present in the original trial directory; numeric diagnostics and probes only were retained.",
            "pending_fixes": "Pending worktree fixes were not edited, reverted, or inferred by this tool; preservation outputs are separate from the worktree.",
            "geometry_execution": "No old trial, geometry builder, renderer, or geometry import was executed by this tool.",
        },
        "render_files_found": render_files,
        "command": [sys.executable, str(Path(__file__).resolve()), "--preserve-prefilter", str(output)],
    }
    write_json(output / "preservation-manifest.json", manifest)
    print(f"preserved {len(raw_rows)} raw files at {raw_destination}")
    print(f"recovery snapshot: {recovery_destination}")
    print(f"manifest: {output / 'preservation-manifest.json'}")


def snapshot(root: Path, output: Path) -> None:
    root = root.resolve()
    if not root.is_dir() or root.is_symlink():
        fail(f"snapshot root is unavailable: {root}")
    output = output.absolute()
    if output == root or root in output.parents:
        fail("snapshot output must not be inside the source root")
    fresh_directory(output)
    files = source_files(root)
    rows = copy_files(root, files, output / "source")
    environment = environment_snapshot()
    runtime = clone_runtime(output / "runtime")
    environment["runtime_clone"] = runtime
    write_json(output / "environment.json", environment)
    write_json(
        output / "manifest.json",
        {
            "schema": "pelvis-thigh-transition-source-snapshot.v1",
            "source_root": str(root),
            "source": rows,
            "environment": "environment.json",
            "runtime": runtime,
            "exclusions": sorted(EXCLUDED_PARTS),
            "symlinks": "rejected",
            "source_hashing": "inventory hashed before and after copy; copied bytes are compared to source-before identity; drift fails closed",
        },
    )
    print(f"snapshotted {len(rows)} files at {output / 'source'}")
    print(f"manifest: {output / 'manifest.json'}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--preserve-prefilter", metavar="OUT")
    modes.add_argument("--snapshot", metavar="ROOT")
    parser.add_argument("--output", metavar="OUT")
    args = parser.parse_args()
    if args.preserve_prefilter:
        if args.output:
            parser.error("--output is only valid with --snapshot")
        preserve(Path(args.preserve_prefilter).absolute())
    else:
        if not args.output:
            parser.error("--snapshot requires --output OUT")
        snapshot(Path(args.snapshot), Path(args.output))


if __name__ == "__main__":
    main()

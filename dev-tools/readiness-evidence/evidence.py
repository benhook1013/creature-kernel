#!/usr/bin/env python3
"""Emit deterministic, evidence-only inputs for the Readiness 2 review.

This module intentionally does not decide, record, or activate admission.  It
collects the parser-independent fixture preflight result and separately
domain-separated identities for implementation bytes, admission support,
Cargo.lock plus the resolved dependency graph, and the locked/offline build
request.
"""

from __future__ import annotations

import argparse
import errno
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import struct
import subprocess
import sys
try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - only Python 3.10 compatibility
    tomllib = None  # type: ignore[assignment]
from typing import Any, Iterable


ROOT_MANIFEST = "fixtures/body-documents/readiness-2/manifest.v1.json"
IMPLEMENTATION_PATHS = (
    "Cargo.toml",
    "Cargo.lock",
    "rust-toolchain.toml",
    "crates/creature-kernel-cli/Cargo.toml",
    "crates/creature-kernel-core/Cargo.toml",
    "crates/creature-kernel-core/src/lib.rs",
    "crates/creature-kernel-core/src/body_document.rs",
    "spec/body-document/schema/ck-body-document-v1.schema.json",
)
ABSENT_IMPLEMENTATION_PATH = ".cargo/config.toml"
ADMISSION_SUPPORT_PATHS = (
    "dev-tools/fixture-preflight/preflight.py",
    "dev-tools/readiness-evidence/evidence.py",
    "spec/fixture-manifest/schema/ck-fixture-manifest-v1.schema.json",
)
TARGET = "x86_64-unknown-linux-gnu"
TOOLCHAIN = "1.97.1"
PACKAGE = "creature-kernel-core"
FEATURES = ["default"]
PROFILE = "dev"
ENVIRONMENT_POLICY = "ck.sanitized-child-environment.v1"
CARGO_CONFIG_POLICY = "ck.reject-cargo-config-ancestors-and-home.v1"
TARGET_PROJECTION_POLICY = "ck.exact-workspace-targets.v1"
TEST_ARGS = (
    "test",
    "-p",
    PACKAGE,
    "--all-targets",
    "--target",
    TARGET,
    "--locked",
    "--offline",
)
CLIPPY_ARGS = (
    "clippy",
    "-p",
    PACKAGE,
    "--all-targets",
    "--target",
    TARGET,
    "--locked",
    "--offline",
    "--",
    "-D",
    "warnings",
)
COMMANDS = [
    "cargo " + " ".join(TEST_ARGS),
    "cargo " + " ".join(CLIPPY_ARGS),
]

# Cargo's metadata target objects are part of the bound build request.  These
# are the only workspace targets admitted by the two package manifests.  The
# source paths are normalized relative to the workspace root before comparison
# so a checkout's absolute location is not an identity input.
EXPECTED_TARGETS = {
    "creature-kernel-core": {
        "version": "0.1.0",
        "manifest_path": "crates/creature-kernel-core/Cargo.toml",
        "targets": [
            {
                "crate_types": ["lib"],
                "doc": True,
                "doctest": True,
                "edition": "2024",
                "kind": ["lib"],
                "name": "creature_kernel_core",
                "src_path": "crates/creature-kernel-core/src/lib.rs",
                "test": True,
            }
        ],
    },
    "creature-kernel-cli": {
        "version": "0.1.0",
        "manifest_path": "crates/creature-kernel-cli/Cargo.toml",
        "targets": [
            {
                "crate_types": ["bin"],
                "doc": True,
                "doctest": False,
                "edition": "2024",
                "kind": ["bin"],
                "name": "creature-kernel",
                "src_path": "crates/creature-kernel-cli/src/main.rs",
                "test": True,
            }
        ],
    },
}

# The child environment is deliberately narrow with respect to build
# controls.  Generic process context (for example PATH and HOME) remains for
# rustup and the registry cache, but Cargo/Rust/compiler/profile overrides and
# wrappers never cross the boundary.  CARGO_HOME and RUSTUP_TOOLCHAIN are set
# below to exact values after ambient values are discarded.
_CLEAR_ENV_EXACT = {
    "AR",
    "CC",
    "CFLAGS",
    "CPPFLAGS",
    "CXX",
    "CXXFLAGS",
    "LD",
    "LDFLAGS",
    "MAKE",
    "MAKEFLAGS",
    "PKG_CONFIG_PATH",
    "RANLIB",
    "RUSTC",
    "RUSTDOC",
    "RUSTFMT",
    "RUSTUP_TOOLCHAIN",
    "RUSTC_BOOTSTRAP",
    "RUSTC_FORCE_UNSTABLE",
    "RUSTC_LOG",
    "RUSTC_WRAPPER",
    "RUSTC_WORKSPACE_WRAPPER",
    "RUSTFLAGS",
    "RUSTDOCFLAGS",
    "PROFILE",
}
_PREFLIGHT: Any | None = None


class EvidenceError(Exception):
    """A concise deterministic failure suitable for CLI stderr."""


def _preflight_module() -> Any:
    global _PREFLIGHT
    if _PREFLIGHT is not None:
        return _PREFLIGHT
    path = Path(__file__).resolve().parent.parent / "fixture-preflight" / "preflight.py"
    spec = importlib.util.spec_from_file_location("creature_kernel_fixture_preflight", path)
    if spec is None or spec.loader is None:
        raise EvidenceError("fixture preflight module is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _PREFLIGHT = module
    return module


def _read_optional_relative(root_fd: int, path: str) -> tuple[bytes, int] | None:
    """Read an optional path, using the same no-follow traversal as preflight.

    Missing final entries (or a missing ancestor directory) mean explicit
    absence.  Symlinks, special files, hardlinks, bad modes, and traversal are
    still errors because present entries must satisfy the shared reader's
    safety profile.
    """
    preflight = _preflight_module()
    preflight._safe_path(path, "implementation path")
    ancestors: list[int] = []
    current = root_fd
    components = preflight._path_components(path)
    try:
        for component in components[:-1]:
            try:
                next_fd = os.open(
                    component,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                    dir_fd=current,
                )
            except OSError as exc:
                if exc.errno == errno.ENOENT:
                    return None
                raise preflight.PreflightError("path ancestor is invalid") from exc
            info = os.fstat(next_fd)
            if not stat.S_ISDIR(info.st_mode):
                os.close(next_fd)
                raise preflight.PreflightError("path ancestor is invalid")
            ancestors.append(next_fd)
            current = next_fd
        try:
            fd = os.open(
                components[-1],
                os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=current,
            )
        except OSError as exc:
            if exc.errno == errno.ENOENT:
                return None
            raise preflight.PreflightError("path file is unavailable") from exc
        os.close(fd)
        # Delegate all present-file checks and byte reads to the canonical
        # parser-independent preflight reader.
        return preflight._read_relative(root_fd, path)
    finally:
        for ancestor_fd in reversed(ancestors):
            os.close(ancestor_fd)


def _read_binding_file(root_fd: int, path: str) -> tuple[bytes, int]:
    """Apply path validation before delegating to the shared safe reader."""
    preflight = _preflight_module()
    preflight._safe_path(path, "binding path")
    return preflight._read_relative(root_fd, path)


def _raw_binding(
    framing: str, entries: Iterable[tuple[str, int, bytes]]
) -> str:
    """Hash sorted path/mode/raw-byte records using fixture-preflight framing."""
    digest = hashlib.sha256()
    digest.update(framing.encode("ascii") + b"\0")
    seen: set[str] = set()
    for path, mode, content in sorted(entries, key=lambda item: item[0].encode("utf-8")):
        if path in seen:
            raise EvidenceError("duplicate path in content binding")
        seen.add(path)
        path_bytes = path.encode("utf-8")
        digest.update(struct.pack(">I", len(path_bytes)))
        digest.update(path_bytes)
        digest.update(struct.pack(">I", mode))
        digest.update(struct.pack(">Q", len(content)))
        digest.update(content)
    return digest.hexdigest()


def implementation_binding(root: str) -> dict[str, Any]:
    preflight = _preflight_module()
    root_fd = preflight._open_root(root)
    try:
        entries: list[tuple[str, int, bytes]] = []
        for path in IMPLEMENTATION_PATHS:
            content, mode = _read_binding_file(root_fd, path)
            entries.append((path, mode, content))
        absent = _read_optional_relative(root_fd, ABSENT_IMPLEMENTATION_PATH)
        if absent is not None:
            # Keep the absence marker's path distinct from the regular path
            # list, but bind a present config with its actual bytes.
            content, mode = absent
            entries.append((ABSENT_IMPLEMENTATION_PATH, mode, content))
            absent_paths: list[str] = []
        else:
            # Mode zero and empty content are the explicit absence record. It
            # uses the exact same path/mode/length framing as regular entries.
            entries.append((ABSENT_IMPLEMENTATION_PATH, 0, b""))
            absent_paths = [ABSENT_IMPLEMENTATION_PATH]
        return {
            "framing": "ck.implementation-path-set.raw.v1",
            "sha256": _raw_binding("ck.implementation-path-set.raw.v1", entries),
            "paths": sorted(IMPLEMENTATION_PATHS),
            "absent_paths": absent_paths,
        }
    finally:
        os.close(root_fd)


def admission_support_binding(root: str) -> dict[str, Any]:
    """Bind the independent preflight and manifest-schema support files.

    These files establish the identity of the admission-support machinery and
    manifest schema.  They are intentionally not included in the production
    implementation binding: preflight is parser-independent and the schema is
    a contract input, not production parser code.
    """
    preflight = _preflight_module()
    root_fd = preflight._open_root(root)
    try:
        entries: list[tuple[str, int, bytes]] = []
        for path in ADMISSION_SUPPORT_PATHS:
            content, mode = _read_binding_file(root_fd, path)
            entries.append((path, mode, content))
    finally:
        os.close(root_fd)
    framing = "ck.readiness-support-path-set.raw.v1"
    return {
        "framing": framing,
        "sha256": _raw_binding(framing, entries),
        "paths": sorted(ADMISSION_SUPPORT_PATHS),
    }


def _require_string(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise EvidenceError(f"Cargo.lock {name} is not a string")
    return value


def _compat_parse_lock(data: bytes) -> dict[str, Any]:
    """Parse Cargo's generated lock projection on Python 3.10 only.

    This is deliberately limited to the TOML constructs Cargo emits for
    package records. The normative path is stdlib ``tomllib`` on Python 3.11+
    and this fallback is not a general TOML parser.
    """
    lines = data.decode("utf-8").splitlines()
    packages: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        index += 1
        if not line or line.startswith("#") or line == "version = 4":
            continue
        if line == "[[package]]":
            current = {}
            packages.append(current)
            continue
        if current is None or "=" not in line:
            raise ValueError("unsupported Cargo.lock TOML")
        key, value = (part.strip() for part in line.split("=", 1))
        if value.startswith("[") and not value.rstrip().endswith("]"):
            parts = [value]
            while index < len(lines):
                parts.append(lines[index].strip())
                index += 1
                if parts[-1].endswith("]"):
                    break
            value = " ".join(parts)
        if value.startswith("["):
            value = value.replace(",]", "]").replace(", ]", " ]")
            value = value.replace(", ]", "]")
            parsed = json.loads(value)
        else:
            parsed = json.loads(value)
        current[key] = parsed
    return {"package": packages}


def _parse_lock(lock_bytes: bytes) -> list[dict[str, Any]]:
    try:
        if tomllib is not None:
            lock = tomllib.loads(lock_bytes.decode("utf-8"))
        else:
            # Cargo.lock's generated package projection is intentionally a
            # narrow compatibility path for Python 3.10, where stdlib
            # tomllib does not exist. Python 3.11+ always uses tomllib above.
            lock = _compat_parse_lock(lock_bytes)
    except (UnicodeDecodeError, ValueError, KeyError) as exc:
        raise EvidenceError("Cargo.lock is not valid UTF-8 TOML") from exc
    packages_value = lock.get("package")
    if not isinstance(packages_value, list):
        raise EvidenceError("Cargo.lock package table is missing")
    packages: list[dict[str, Any]] = []
    for index, package in enumerate(packages_value):
        if not isinstance(package, dict):
            raise EvidenceError(f"Cargo.lock package[{index}] is not a table")
        name = _require_string(package.get("name"), f"package[{index}].name")
        version = _require_string(package.get("version"), f"package[{index}].version")
        source = package.get("source")
        checksum = package.get("checksum")
        if source is not None:
            source = _require_string(source, f"package[{index}].source")
        if checksum is not None:
            checksum = _require_string(checksum, f"package[{index}].checksum")
        dependencies = package.get("dependencies", [])
        if not isinstance(dependencies, list) or not all(isinstance(item, str) for item in dependencies):
            raise EvidenceError(f"Cargo.lock package[{index}].dependencies is invalid")
        packages.append(
            {
                "name": name,
                "version": version,
                "source": source,
                "checksum": checksum,
                "dependencies": list(dependencies),
            }
        )
    return packages


def _cargo_home() -> Path:
    """Resolve the Cargo home used by the sanitized child environment."""
    home = os.environ.get("HOME")
    if home is None:
        home = str(Path.home())
    return (Path(home).expanduser() / ".cargo").resolve()


def _cargo_config_paths(root: str, cargo_home: Path) -> list[Path]:
    """Return every current/legacy Cargo config Cargo could consult."""
    paths: list[Path] = []
    current = Path(root).resolve()
    while True:
        for filename in ("config.toml", "config"):
            paths.append(current / ".cargo" / filename)
        parent = current.parent
        if parent == current:
            break
        current = parent
    for filename in ("config.toml", "config"):
        paths.append(cargo_home / filename)
    return paths


def _reject_cargo_configs(root: str, cargo_home: Path) -> None:
    """Fail closed when Cargo configuration could change the bound request."""
    for path in _cargo_config_paths(root, cargo_home):
        # lexists also rejects a dangling symlink: it is still an uncontrolled
        # configuration input even when its target is unavailable.
        if os.path.lexists(path):
            raise EvidenceError(f"Cargo config is not permitted: {path}")


def sanitized_environment(root: str) -> dict[str, str]:
    """Build the exact environment policy used by metadata and bound checks."""
    cargo_home = _cargo_home()
    _reject_cargo_configs(root, cargo_home)
    environment: dict[str, str] = {}
    for key, value in os.environ.items():
        if key.startswith("CARGO_") or key.startswith("RUST") or key in _CLEAR_ENV_EXACT:
            continue
        environment[key] = value
    # These are fixed request inputs, not inherited overrides.  Cargo home
    # contents remain external dependency-cache evidence; their config files
    # are rejected above rather than pretending to be vendored or hermetic.
    environment["CARGO_HOME"] = str(cargo_home)
    environment["RUSTUP_TOOLCHAIN"] = TOOLCHAIN
    return environment


def _cargo_metadata(root: str) -> dict[str, Any]:
    """Return the locked/offline Cargo resolution or fail closed.

    The caller must arrange any local registry/cache setup before invoking the
    generator.  In particular, this function never retries without ``--offline``
    or falls back to Cargo.lock when metadata resolution is unavailable.
    """
    try:
        result = subprocess.run(
            [
                _tool("cargo"),
                "metadata",
                "--format-version",
                "1",
                "--locked",
                "--offline",
                "--filter-platform",
                TARGET,
            ],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            env=sanitized_environment(root),
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise EvidenceError("cargo metadata --locked --offline failed; dependencies must be locally available") from exc
    try:
        metadata = json.loads(result.stdout)
    except (TypeError, json.JSONDecodeError) as exc:
        raise EvidenceError("cargo metadata returned invalid JSON") from exc
    if not isinstance(metadata, dict):
        raise EvidenceError("cargo metadata result is not an object")
    metadata_root = metadata.get("workspace_root")
    if not isinstance(metadata_root, str) or Path(metadata_root).resolve() != Path(root).resolve():
        raise EvidenceError("cargo metadata workspace root does not match the requested checkout")
    return metadata


def _ascii_json(value: Any) -> bytes:
    """Serialize an evidence projection using its declared ASCII JSON form."""
    try:
        serialized = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return serialized.encode("ascii")
    except (TypeError, UnicodeEncodeError, ValueError) as exc:
        raise EvidenceError("dependency projection is not serializable ASCII JSON") from exc


def _target_projection(metadata: dict[str, Any], workspace_root: Path) -> dict[str, Any]:
    """Validate and return the exact workspace target projection."""
    packages_value = metadata.get("packages")
    members_value = metadata.get("workspace_members")
    if not isinstance(packages_value, list) or not isinstance(members_value, list):
        raise EvidenceError("cargo metadata packages/workspace members are missing")
    package_by_id: dict[str, dict[str, Any]] = {}
    for index, package in enumerate(packages_value):
        if not isinstance(package, dict) or not isinstance(package.get("id"), str):
            raise EvidenceError(f"cargo metadata package[{index}] is invalid")
        package_id = package["id"]
        if package_id in package_by_id:
            raise EvidenceError("cargo metadata package IDs are duplicated")
        package_by_id[package_id] = package
    if not all(isinstance(member, str) for member in members_value):
        raise EvidenceError("cargo metadata workspace members are invalid")
    if len(set(members_value)) != len(members_value):
        raise EvidenceError("cargo metadata workspace members are duplicated")
    member_packages: list[dict[str, Any]] = []
    for member_id in members_value:
        package = package_by_id.get(member_id)
        if package is None:
            raise EvidenceError("cargo metadata workspace member is unknown")
        member_packages.append(package)
    member_names = [package.get("name") for package in member_packages]
    if not all(isinstance(name, str) for name in member_names):
        raise EvidenceError("cargo metadata workspace member names are invalid")
    if set(member_names) != set(EXPECTED_TARGETS) or len(member_names) != len(EXPECTED_TARGETS):
        raise EvidenceError("cargo metadata workspace members are not the bound packages")

    projection: list[dict[str, Any]] = []
    for name in sorted(EXPECTED_TARGETS):
        expected = EXPECTED_TARGETS[name]
        package = next((item for item in member_packages if item.get("name") == name), None)
        if package is None:
            raise EvidenceError(f"cargo metadata is missing workspace package {name}")
        if package.get("version") != expected["version"]:
            raise EvidenceError(f"cargo metadata package {name} has an unexpected version")
        manifest_path = package.get("manifest_path")
        if not isinstance(manifest_path, str):
            raise EvidenceError(f"cargo metadata package {name} lacks manifest_path")
        try:
            relative_manifest = Path(manifest_path).resolve().relative_to(workspace_root)
        except ValueError as exc:
            raise EvidenceError(f"cargo metadata package {name} is outside the workspace root") from exc
        if relative_manifest.as_posix() != expected["manifest_path"]:
            raise EvidenceError(f"cargo metadata package {name} has an unexpected manifest")
        targets = package.get("targets")
        if not isinstance(targets, list):
            raise EvidenceError(f"cargo metadata package {name} targets are missing")
        normalized_targets: list[dict[str, Any]] = []
        for index, target in enumerate(targets):
            if not isinstance(target, dict):
                raise EvidenceError(f"cargo metadata package {name} target[{index}] is invalid")
            normalized = dict(target)
            source_path = normalized.get("src_path")
            if not isinstance(source_path, str):
                raise EvidenceError(f"cargo metadata package {name} target[{index}] lacks src_path")
            try:
                relative_source = Path(source_path).resolve().relative_to(workspace_root)
            except ValueError as exc:
                raise EvidenceError(
                    f"cargo metadata package {name} target[{index}] is outside the workspace root"
                ) from exc
            normalized["src_path"] = relative_source.as_posix()
            normalized_targets.append(normalized)
        if normalized_targets != expected["targets"]:
            raise EvidenceError(f"cargo metadata package {name} targets do not match the bound projection")
        projection.append(
            {
                "manifest_path": expected["manifest_path"],
                "name": name,
                "targets": normalized_targets,
                "version": expected["version"],
            }
        )
    return {"workspace_members": projection}


def _dependency_projection(
    metadata: dict[str, Any], lock_packages: list[dict[str, Any]]
) -> dict[str, Any]:
    packages_value = metadata.get("packages")
    resolve = metadata.get("resolve")
    workspace_root_value = metadata.get("workspace_root")
    if (
        not isinstance(packages_value, list)
        or not isinstance(resolve, dict)
        or not isinstance(workspace_root_value, str)
    ):
        raise EvidenceError("cargo metadata packages/resolve/workspace root are missing")
    workspace_root = Path(workspace_root_value).resolve()
    target_projection = _target_projection(metadata, workspace_root)
    package_by_id: dict[str, dict[str, Any]] = {}
    for index, package in enumerate(packages_value):
        if not isinstance(package, dict):
            raise EvidenceError(f"cargo metadata package[{index}] is not an object")
        package_id = package.get("id")
        if not isinstance(package_id, str) or package_id in package_by_id:
            raise EvidenceError("cargo metadata package IDs are missing or duplicated")
        package_by_id[package_id] = package

    nodes_value = resolve.get("nodes")
    if not isinstance(nodes_value, list):
        raise EvidenceError("cargo metadata resolve nodes are missing")
    node_by_id: dict[str, dict[str, Any]] = {}
    for index, node in enumerate(nodes_value):
        if not isinstance(node, dict) or not isinstance(node.get("id"), str):
            raise EvidenceError(f"cargo metadata resolve node[{index}] is invalid")
        node_id = node["id"]
        if node_id in node_by_id:
            raise EvidenceError("cargo metadata resolve node IDs are duplicated")
        node_by_id[node_id] = node

    core_ids = [
        package_id
        for package_id, package in package_by_id.items()
        if package.get("name") == PACKAGE
    ]
    if len(core_ids) != 1:
        raise EvidenceError("cargo metadata does not identify exactly one creature-kernel-core package")
    core_id = core_ids[0]
    if core_id not in node_by_id:
        raise EvidenceError("cargo metadata has no resolve node for creature-kernel-core")

    reachable: set[str] = set()
    pending = [core_id]
    while pending:
        package_id = pending.pop()
        if package_id in reachable:
            continue
        node = node_by_id.get(package_id)
        if node is None or package_id not in package_by_id:
            raise EvidenceError("cargo metadata dependency graph references an unknown package")
        reachable.add(package_id)
        dependencies = node.get("deps", [])
        if not isinstance(dependencies, list):
            raise EvidenceError("cargo metadata resolve dependencies are invalid")
        for dependency in dependencies:
            if not isinstance(dependency, dict) or not isinstance(dependency.get("pkg"), str):
                raise EvidenceError("cargo metadata resolve dependency is invalid")
            pending.append(dependency["pkg"])

    lock_by_locator: dict[tuple[str, str, str | None], list[dict[str, Any]]] = {}
    for package in lock_packages:
        key = (package["name"], package["version"], package["source"])
        lock_by_locator.setdefault(key, []).append(package)

    stable_id_by_cargo_id: dict[str, str] = {}
    for package_id in reachable:
        package = package_by_id[package_id]
        name = package.get("name")
        version = package.get("version")
        source = package.get("source")
        if not all(isinstance(value, str) for value in (name, version)):
            raise EvidenceError(f"cargo metadata package {package_id!r} lacks name/version")
        if source is not None and not isinstance(source, str):
            raise EvidenceError(f"cargo metadata package {package_id!r} has an invalid source")
        if source is None:
            manifest_path = package.get("manifest_path")
            if not isinstance(manifest_path, str):
                raise EvidenceError(f"repository package {package_id!r} lacks manifest_path")
            try:
                relative_manifest = Path(manifest_path).resolve().relative_to(workspace_root)
            except ValueError as exc:
                raise EvidenceError(
                    f"repository package {package_id!r} is outside the workspace root"
                ) from exc
            relative_directory = relative_manifest.parent.as_posix()
            stable_id = f"path+workspace://{relative_directory}#{name}@{version}"
        else:
            stable_id = package_id
        if stable_id in stable_id_by_cargo_id.values():
            raise EvidenceError("normalized Cargo package identities are duplicated")
        stable_id_by_cargo_id[package_id] = stable_id

    projection_packages: list[dict[str, Any]] = []
    for package_id in sorted(reachable, key=stable_id_by_cargo_id.__getitem__):
        package = package_by_id[package_id]
        node = node_by_id[package_id]
        name = package.get("name")
        version = package.get("version")
        source = package.get("source")
        license_expression = package.get("license")
        native_links = package.get("links")
        if not all(isinstance(value, str) for value in (name, version)):
            raise EvidenceError(f"cargo metadata package {package_id!r} lacks name/version")
        if source is not None and not isinstance(source, str):
            raise EvidenceError(f"cargo metadata package {package_id!r} has an invalid source")
        if license_expression is not None and not isinstance(license_expression, str):
            raise EvidenceError(f"cargo metadata package {package_id!r} has an invalid license")
        if native_links is not None and not isinstance(native_links, str):
            raise EvidenceError(f"cargo metadata package {package_id!r} has invalid native links")
        lock_matches = lock_by_locator.get((name, version, source), [])
        if len(lock_matches) > 1:
            raise EvidenceError(f"Cargo.lock has ambiguous package locator for {package_id!r}")
        checksum = package.get("checksum")
        if checksum is None and lock_matches:
            checksum = lock_matches[0]["checksum"]
        if checksum is not None and not isinstance(checksum, str):
            raise EvidenceError(f"cargo metadata package {package_id!r} has an invalid checksum")
        features = node.get("features", [])
        if not isinstance(features, list) or not all(isinstance(feature, str) for feature in features):
            raise EvidenceError(f"cargo metadata package {package_id!r} has invalid features")
        dependencies = node.get("deps", [])
        dependency_ids: list[str] = []
        for dependency in dependencies:
            dependency_id = dependency.get("pkg") if isinstance(dependency, dict) else None
            if not isinstance(dependency_id, str):
                raise EvidenceError(f"cargo metadata package {package_id!r} has invalid dependencies")
            stable_dependency_id = stable_id_by_cargo_id.get(dependency_id)
            if stable_dependency_id is None:
                raise EvidenceError(
                    f"cargo metadata package {package_id!r} references an unreachable dependency"
                )
            dependency_ids.append(stable_dependency_id)
        projection_packages.append(
            {
                "checksum": checksum,
                "dependencies": sorted(dependency_ids),
                "features": sorted(features),
                "id": stable_id_by_cargo_id[package_id],
                "license": license_expression,
                "links": native_links,
                "name": name,
                "source": source,
                "version": version,
            }
        )
    return {"packages": projection_packages, "targets": target_projection}


def dependency_closure(
    root: str,
    *,
    metadata: dict[str, Any] | None = None,
    projection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    preflight = _preflight_module()
    root_fd = preflight._open_root(root)
    try:
        lock_bytes, _ = _read_binding_file(root_fd, "Cargo.lock")
    finally:
        os.close(root_fd)
    lock_packages = _parse_lock(lock_bytes)
    if projection is None:
        projection = _dependency_projection(metadata if metadata is not None else _cargo_metadata(root), lock_packages)
    projection_bytes = _ascii_json(projection)
    digest = hashlib.sha256()
    digest.update(b"ck.cargo-lock.dependency-closure.v1\0")
    digest.update(struct.pack(">Q", len(lock_bytes)))
    digest.update(lock_bytes)
    digest.update(struct.pack(">Q", len(projection_bytes)))
    digest.update(projection_bytes)
    return {
        "framing": "ck.cargo-lock.dependency-closure.v1",
        "sha256": digest.hexdigest(),
        "cargo_lock_sha256": hashlib.sha256(lock_bytes).hexdigest(),
        "source_kind": "cargo-metadata-resolved-reachable-graph",
        "projection": projection,
        "projection_json": projection_bytes.decode("ascii"),
    }


def _ascii_atom(value: str) -> bytes:
    encoded = value.encode("ascii")
    return str(len(encoded)).encode("ascii") + b":" + encoded


def _ascii_list(values: Iterable[str]) -> bytes:
    items = list(values)
    return str(len(items)).encode("ascii") + b":" + b"".join(_ascii_atom(item) for item in items)


def build_request(
    implementation_sha256: str,
    dependency_closure_sha256: str,
    admission_support_sha256: str,
) -> dict[str, Any]:
    fields: list[tuple[str, str | list[str]]] = [
        ("target", TARGET),
        ("toolchain", TOOLCHAIN),
        ("package", PACKAGE),
        ("features", FEATURES),
        ("profile", PROFILE),
        ("environment_policy", ENVIRONMENT_POLICY),
        ("cargo_config_policy", CARGO_CONFIG_POLICY),
        ("target_projection_policy", TARGET_PROJECTION_POLICY),
        ("commands", COMMANDS),
        ("implementation_sha256", implementation_sha256),
        ("dependency_closure_sha256", dependency_closure_sha256),
        ("admission_support_sha256", admission_support_sha256),
    ]
    encoded = bytearray(b"ck.rust-build-request.v1\0")
    for name, value in fields:
        encoded.extend(_ascii_atom(name))
        if isinstance(value, list):
            encoded.extend(_ascii_list(value))
        else:
            encoded.extend(_ascii_atom(value))
    return {
        "framing": "ck.rust-build-request.v1",
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "target": TARGET,
        "toolchain": TOOLCHAIN,
        "package": PACKAGE,
        "features": FEATURES,
        "profile": PROFILE,
        "environment_policy": ENVIRONMENT_POLICY,
        "cargo_config_policy": CARGO_CONFIG_POLICY,
        "target_projection_policy": TARGET_PROJECTION_POLICY,
        "commands": COMMANDS,
        "implementation_sha256": implementation_sha256,
        "dependency_closure_sha256": dependency_closure_sha256,
        "admission_support_sha256": admission_support_sha256,
    }


def _tool(name: str) -> str:
    home_tool = Path.home() / ".cargo" / "bin" / name
    if os.access(home_tool, os.X_OK):
        return str(home_tool)
    found = shutil.which(name)
    if found:
        return found
    fallback = f"/home/ben/.cargo/bin/{name}"
    if os.access(fallback, os.X_OK):
        return fallback
    raise EvidenceError(f"{name} executable is unavailable")


def environment_evidence(root: str) -> dict[str, str]:
    environment = sanitized_environment(root)
    try:
        rustc = subprocess.run(
            [_tool("rustc"), "-Vv"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )
        cargo = subprocess.run(
            [_tool("cargo"), "-V"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise EvidenceError("toolchain evidence command failed") from exc
    rustc_vv = rustc.stdout.strip()
    cargo_v = cargo.stdout.strip()
    values: dict[str, str] = {}
    for line in rustc_vv.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip()
    if values.get("release") != TOOLCHAIN or values.get("host") != TARGET:
        raise EvidenceError("active rustc release/host does not match build request")
    return {"rustc_vv": rustc_vv, "cargo_v": cargo_v}


def run_bound_checks(root: str) -> None:
    """Run the exact core test/lint request in the sanitized environment."""
    environment = sanitized_environment(root)
    cargo = _tool("cargo")
    for args in (TEST_ARGS, CLIPPY_ARGS):
        try:
            subprocess.run([cargo, *args], cwd=root, check=True, env=environment)
        except (OSError, subprocess.CalledProcessError) as exc:
            command = "cargo " + " ".join(args)
            raise EvidenceError(f"bound command failed: {command}") from exc


def fetch_locked(root: str) -> None:
    """Fetch the lockfile's dependencies before the offline bound checks."""
    environment = sanitized_environment(root)
    try:
        subprocess.run(
            [_tool("cargo"), "fetch", "--locked"],
            cwd=root,
            check=True,
            env=environment,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise EvidenceError("locked dependency fetch failed") from exc


def generate(root: str) -> dict[str, Any]:
    preflight = _preflight_module()
    try:
        fixture_payload = preflight.run(root, ROOT_MANIFEST)
    except preflight.PreflightError as exc:
        raise EvidenceError(f"fixture preflight failed: {exc.message}") from exc
    implementation = implementation_binding(root)
    admission_support = admission_support_binding(root)
    dependency = dependency_closure(root)
    return {
        "contract": {"family": "creature-kernel.readiness-evidence", "revision": 1, "stage": "readiness-2"},
        "fixture_payload": fixture_payload,
        "implementation": implementation,
        "admission_support": admission_support,
        "dependency_closure": dependency,
        "build_request": build_request(
            implementation["sha256"],
            dependency["sha256"],
            admission_support["sha256"],
        ),
        "environment_evidence": environment_evidence(root),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="emit Readiness 2 evidence (does not admit or activate)")
    parser.add_argument("repository_root", nargs="?", default=".")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument(
        "--run-bound-checks",
        action="store_true",
        help="run the exact sanitized core test and clippy request instead of emitting JSON",
    )
    modes.add_argument(
        "--fetch-locked",
        action="store_true",
        help="fetch Cargo.lock dependencies with the sanitized environment",
    )
    args = parser.parse_args(argv)
    try:
        if args.run_bound_checks:
            run_bound_checks(args.repository_root)
            return 0
        if args.fetch_locked:
            fetch_locked(args.repository_root)
            return 0
        result = generate(args.repository_root)
    except EvidenceError as exc:
        print(f"readiness-evidence: {exc}", file=sys.stderr)
        return 1
    print(__import__("json").dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

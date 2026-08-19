#!/usr/bin/env python3
"""Capture a build-only, transferable receipt for the Phase 3 candidate.

This tool accepts an already-built ELF and caller-supplied build metadata.  It
never starts the ELF, feeds it input, or dispatches an experiment.  The source
closure is recomputed from the repository's Gate-A prebinding checker and the
binary, lockfile, and Cargo metadata are read only.

The receipt is intentionally small: large source and dependency inputs are
represented by bounded identities rather than copied into the receipt.  A
domain-framed self-hash makes the exact canonical JSON receipt portable.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import posixpath
import re
import stat
import struct
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Mapping

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised on Python 3.10
    tomllib = None  # type: ignore[assignment]


PHASE_ID = "exp-0002-phase3-semantic-band-conformance-001"
GIT_EXECUTABLE = "/usr/bin/git"
# Receipt source/working-tree reads are intentionally independent of ambient
# locale, Git configuration, home, and optional lock behaviour.  This exact
# closed environment is also applied when the module is loaded by freeze.
GIT_ENV = {
    "LANG": "C",
    "LC_ALL": "C",
    "LC_CTYPE": "C",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_SYSTEM": "/dev/null",
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "HOME": "/nonexistent",
    "XDG_CONFIG_HOME": "/nonexistent",
    "XDG_CACHE_HOME": "/nonexistent",
    "GIT_OPTIONAL_LOCKS": "0",
}
RECEIPT_SCHEMA = "ck.exp-0002.phase3.gate-b-build-receipt-1"
METADATA_SCHEMA = "ck.exp-0002.phase3.gate-b-build-metadata-1"
DEPENDENCY_SCHEMA = "ck.exp-0002.phase3.gate-b-cargo-metadata-1"
SELF_HASH_DOMAIN = b"ck.exp-0002.phase3.gate-b-build-receipt-self.v1\0"
DEPENDENCY_HASH_DOMAIN = b"ck.exp-0002.phase3.gate-b-dependency-closure.v1\0"
VENDOR_HASH_DOMAIN = b"ck.exp-0002.phase3.gate-b-vendor-closure.v1\0"
TARGET = "x86_64-unknown-linux-gnu"
PROFILE = "dev"
TOOLCHAIN = "1.97.1"
CANDIDATE_PROFILE_ID = "ck.provisional-r3-authored-conflict.semantic-band-1"
CANDIDATE_MANIFEST = "experiments/EXP-0002-numeric-frame-profile/phase2-authored-conflict/candidate/Cargo.toml"
CANDIDATE_LOCK = "experiments/EXP-0002-numeric-frame-profile/phase2-authored-conflict/candidate/Cargo.lock"
CANDIDATE_PACKAGE_NAME = "exp-0002-r3-authored-conflict-candidate"
CANDIDATE_PACKAGE_VERSION = "0.1.0"
CORE_MANIFEST = "crates/creature-kernel-core/Cargo.toml"
REGISTRY_SOURCE = "registry+https://github.com/rust-lang/crates.io-index"
VENDOR_CHECKSUM_COMMENT = "This file only protects against accidental modifications. It is not a security mechanism and does not protect against malicious changes."
PLATFORM_ROLES = frozenset({"wsl", "native"})
ENV_POLICY_VALUES = {
    "PATH": "<tool-path>",
    "HOME": "<build-home>",
    "CARGO_HOME": "<cargo-home>",
    "RUSTUP_HOME": "<rustup-home>",
    "CARGO_NET_OFFLINE": "true",
    "CARGO_TARGET_DIR": "<fresh-target-dir>",
    "TMPDIR": "<runner-temp>",
}
MAX_METADATA_BYTES = 4 * 1024 * 1024
MAX_RECEIPT_BYTES = 128 * 1024
MAX_VENDOR_FILE_BYTES = 64 * 1024 * 1024
MAX_VENDOR_TOTAL_BYTES = 512 * 1024 * 1024
MAX_BINARY_BYTES = 512 * 1024 * 1024
FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class ReceiptError(ValueError):
    """A fail-closed build receipt error."""


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _no_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ReceiptError(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def _json_file(path: Path, label: str) -> dict[str, Any]:
    try:
        raw, _ = _read_regular_file(path, label, max_bytes=MAX_METADATA_BYTES)
    except ReceiptError:
        raise
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicate_pairs)
    except RecursionError as error:
        raise ReceiptError(f"{label} exceeds the bounded JSON nesting depth") from error
    except (UnicodeDecodeError, json.JSONDecodeError, ReceiptError) as error:
        raise ReceiptError(f"{label} is not valid JSON: {error}") from error
    if type(value) is not dict:
        raise ReceiptError(f"{label} must be a JSON object")
    return value


def _file_identity(info: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _regular_fd(path: Path, label: str) -> tuple[int, os.stat_result]:
    """Open a regular file without following its final path component.

    The path is checked before and after opening so a replacement between the
    path lookup and ``open`` is rejected.  Consumers also compare the fd's
    identity after reading, preventing a changed or truncated file from being
    silently represented by a receipt.
    """
    try:
        path_info = path.lstat()
    except OSError as error:
        raise ReceiptError(f"cannot stat {label}: {error}") from error
    if stat.S_ISLNK(path_info.st_mode) or not stat.S_ISREG(path_info.st_mode):
        raise ReceiptError(f"{label} must be a regular non-symlink file")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    fd: int | None = None
    try:
        fd = os.open(path, flags)
        fd_info = os.fstat(fd)
        if _file_identity(path_info) != _file_identity(fd_info):
            os.close(fd)
            raise ReceiptError(f"{label} changed while opening")
    except ReceiptError:
        raise
    except OSError as error:
        if fd is not None:
            os.close(fd)
        raise ReceiptError(f"cannot open {label}: {error}") from error
    if stat.S_ISLNK(fd_info.st_mode) or not stat.S_ISREG(fd_info.st_mode):
        os.close(fd)
        raise ReceiptError(f"{label} is not a regular file")
    assert fd is not None
    return fd, fd_info


def _read_regular_file(path: Path, label: str, *, max_bytes: int) -> tuple[bytes, os.stat_result]:
    fd, before = _regular_fd(path, label)
    chunks: list[bytes] = []
    total = 0
    try:
        while True:
            chunk = os.read(fd, min(1024 * 1024, max_bytes - total + 1))
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise ReceiptError(f"{label} exceeds the bounded size")
            chunks.append(chunk)
        after = os.fstat(fd)
    except ReceiptError:
        raise
    except OSError as error:
        raise ReceiptError(f"cannot read {label}: {error}") from error
    finally:
        os.close(fd)
    if _file_identity(before) != _file_identity(after):
        raise ReceiptError(f"{label} changed while reading")
    return b"".join(chunks), after


def _hash_regular_file(path: Path, label: str, *, max_bytes: int, header_bytes: int = 0) -> tuple[str, int, os.stat_result, bytes]:
    """Hash through a checked descriptor, retaining at most *header_bytes*."""
    fd, before = _regular_fd(path, label)
    digest = hashlib.sha256()
    captured = bytearray()
    total = 0
    try:
        while True:
            chunk = os.read(fd, min(1024 * 1024, max_bytes - total + 1))
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise ReceiptError(f"{label} exceeds the bounded size")
            digest.update(chunk)
            if len(captured) < header_bytes:
                captured.extend(chunk[: header_bytes - len(captured)])
        after = os.fstat(fd)
    except ReceiptError:
        raise
    except OSError as error:
        raise ReceiptError(f"cannot read {label}: {error}") from error
    finally:
        os.close(fd)
    if _file_identity(before) != _file_identity(after):
        raise ReceiptError(f"{label} changed while reading")
    return digest.hexdigest(), total, after, bytes(captured)


def _string(value: Any, label: str, *, nonempty: bool = True, max_bytes: int = 4096) -> str:
    if type(value) is not str or (nonempty and not value) or len(value.encode("utf-8")) > max_bytes or "\x00" in value:
        raise ReceiptError(f"{label} is not a bounded string")
    return value


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise ReceiptError(f"{label} has an unexpected or missing field")


def _safe_relative(value: Any, label: str) -> str:
    path = _string(value, label)
    if path.startswith("/") or path.startswith("./") or "\\" in path:
        raise ReceiptError(f"{label} is not a repository-relative POSIX path")
    parts = path.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ReceiptError(f"{label} contains an unsafe path component")
    return path


def _regular_file(path: Path, label: str, *, executable: bool = False) -> os.stat_result:
    try:
        info = path.lstat()
    except OSError as error:
        raise ReceiptError(f"cannot stat {label}: {error}") from error
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise ReceiptError(f"{label} must be a regular non-symlink file")
    if executable and not (info.st_mode & 0o111):
        raise ReceiptError(f"{label} is not executable")
    return info


def _inside(repo: Path, candidate: Path, label: str) -> tuple[Path, str]:
    repo = repo.resolve()
    try:
        lexical = candidate.absolute()
        relative = lexical.relative_to(repo).as_posix()
    except (OSError, ValueError) as error:
        raise ReceiptError(f"{label} must be inside the repository") from error
    _regular_file(lexical, label)
    try:
        resolved = lexical.resolve(strict=True)
    except OSError as error:
        raise ReceiptError(f"{label} cannot be resolved") from error
    if resolved != lexical:
        raise ReceiptError(f"{label} contains a symlinked path component")
    return lexical, _safe_relative(relative, label)


def _sha256(path: Path, label: str = "file", *, max_bytes: int = MAX_METADATA_BYTES) -> tuple[str, int]:
    digest, size, _, _ = _hash_regular_file(path, label, max_bytes=max_bytes)
    return digest, size


def _safe_tree_root(path: Path, label: str) -> Path:
    """Return a directory whose every path component is non-symlink."""
    absolute = path.absolute()
    current = Path(absolute.anchor) if absolute.anchor else Path(".")
    for component in absolute.parts[1:] if absolute.is_absolute() else absolute.parts:
        current /= component
        try:
            info = current.lstat()
        except OSError as error:
            raise ReceiptError(f"cannot stat {label}: {error}") from error
        if stat.S_ISLNK(info.st_mode):
            raise ReceiptError(f"{label} contains a symlinked path component")
        if current != absolute and not stat.S_ISDIR(info.st_mode):
            raise ReceiptError(f"{label} contains a non-directory component")
    if not stat.S_ISDIR(absolute.lstat().st_mode):
        raise ReceiptError(f"{label} is not a directory")
    return absolute


def capture_vendor_closure(vendor: Path) -> dict[str, Any]:
    """Hash every normalized regular file, mode, and raw byte in *vendor*.

    Directory enumeration is path-based but every file's bytes are consumed
    through a descriptor with bounded reads and before/after identity checks.
    This keeps a concurrent replacement from becoming an unreported receipt
    identity.
    """
    root = _safe_tree_root(vendor, "vendor directory")
    entries: list[tuple[str, int, Path]] = []
    stack = [root]
    while stack:
        directory = stack.pop()
        try:
            children = sorted(os.scandir(directory), key=lambda item: item.name.encode("utf-8"), reverse=True)
        except OSError as error:
            raise ReceiptError(f"cannot scan vendor directory: {error}") from error
        for child in children:
            child_path = Path(child.path)
            try:
                info = child_path.lstat()
            except OSError as error:
                raise ReceiptError(f"cannot stat vendor entry: {error}") from error
            if stat.S_ISLNK(info.st_mode):
                raise ReceiptError(f"vendor closure contains a symlink: {child.name}")
            if stat.S_ISDIR(info.st_mode):
                stack.append(child_path)
                continue
            if not stat.S_ISREG(info.st_mode):
                raise ReceiptError(f"vendor closure contains a non-regular entry: {child.name}")
            relative = child_path.relative_to(root).as_posix()
            _safe_relative(relative, "vendor entry")
            entries.append((relative, stat.S_IFREG | stat.S_IMODE(info.st_mode), child_path))
    entries.sort(key=lambda item: item[0].encode("utf-8"))
    path_stream = bytearray(VENDOR_HASH_DOMAIN)
    content_digest = hashlib.sha256(VENDOR_HASH_DOMAIN)
    total_bytes = 0
    for relative, mode, child_path in entries:
        encoded = relative.encode("utf-8")
        path_stream += struct.pack(">I", len(encoded)) + encoded + struct.pack(">I", mode)
        fd, before = _regular_fd(child_path, f"vendor entry {relative}")
        try:
            if before.st_size > MAX_VENDOR_FILE_BYTES:
                raise ReceiptError(f"vendor entry {relative} exceeds the bounded size")
            content_digest.update(struct.pack(">I", len(encoded)) + encoded + struct.pack(">I", mode) + struct.pack(">Q", before.st_size))
            file_bytes = 0
            while True:
                chunk = os.read(fd, min(1024 * 1024, MAX_VENDOR_FILE_BYTES - file_bytes + 1))
                if not chunk:
                    break
                file_bytes += len(chunk)
                total_bytes += len(chunk)
                if file_bytes > MAX_VENDOR_FILE_BYTES or total_bytes > MAX_VENDOR_TOTAL_BYTES:
                    raise ReceiptError("vendor closure exceeds its bounded size")
                content_digest.update(chunk)
            after = os.fstat(fd)
        except ReceiptError:
            raise
        except OSError as error:
            raise ReceiptError(f"cannot read vendor entry {relative}: {error}") from error
        finally:
            os.close(fd)
        if _file_identity(before) != _file_identity(after) or file_bytes != before.st_size:
            raise ReceiptError(f"vendor entry {relative} changed while reading")
    return {
        "algorithm": "ck.exp-0002.phase3.gate-b-vendor-closure.v1",
        "files": len(entries),
        "bytes": total_bytes,
        "path_sha256": hashlib.sha256(bytes(path_stream)).hexdigest(),
        "content_sha256": content_digest.hexdigest(),
    }


def validate_vendor_closure(closure: Mapping[str, Any]) -> None:
    if type(closure) is not dict:
        raise ReceiptError("vendor closure is not an object")
    required = {"algorithm", "files", "bytes", "path_sha256", "content_sha256"}
    _exact_keys(closure, required, "vendor closure")
    if closure["algorithm"] != "ck.exp-0002.phase3.gate-b-vendor-closure.v1":
        raise ReceiptError("vendor closure algorithm is not recognized")
    if any(type(closure[key]) is not int or closure[key] < 0 for key in ("files", "bytes")):
        raise ReceiptError("vendor closure counts are malformed")
    for key in ("path_sha256", "content_sha256"):
        if not isinstance(closure[key], str) or not re.fullmatch(r"[0-9a-f]{64}", closure[key]):
            raise ReceiptError(f"vendor closure {key} is malformed")
    if closure["files"] == 0 or closure["bytes"] == 0:
        raise ReceiptError("vendor closure is empty")


def _elf_identity(header: bytes) -> dict[str, Any]:
    if len(header) < 64 or header[:4] != b"\x7fELF":
        raise ReceiptError("binary is not an ELF64 file")
    if header[4] != 2 or header[5] != 1:
        raise ReceiptError("binary must be little-endian ELF64")
    e_type, e_machine = struct.unpack_from("<HH", header, 16)
    if e_machine != 62:
        raise ReceiptError(f"binary machine is not x86_64: {e_machine}")
    if e_type not in {2, 3}:
        raise ReceiptError(f"binary ELF type is not executable or PIE: {e_type}")
    return {
        "class": "ELF64",
        "data": "little-endian",
        "machine": "x86_64",
        "type": {2: "ET_EXEC", 3: "ET_DYN"}[e_type],
        "osabi": int(header[7]),
        "entry_point": f"0x{struct.unpack_from('<Q', header, 24)[0]:016x}",
    }


def capture_binary(repo: Path, binary: Path, *, recorded_path: str | None = None) -> dict[str, Any]:
    if recorded_path is None:
        resolved, relative = _inside(repo, binary, "binary")
    else:
        relative = _safe_relative(recorded_path, "binary role path")
        resolved = binary.absolute()
        _regular_file(resolved, "binary", executable=True)
        try:
            target = resolved.resolve(strict=True)
        except OSError as error:
            raise ReceiptError("binary cannot be resolved") from error
        if target != resolved:
            raise ReceiptError("binary contains a symlinked path component")
    digest, size, info, header = _hash_regular_file(resolved, "binary", max_bytes=MAX_BINARY_BYTES, header_bytes=64)
    if not (info.st_mode & 0o111):
        raise ReceiptError("binary is not executable")
    return {
        "role": "phase3-candidate",
        "path": relative,
        "sha256": digest,
        "bytes": size,
        "mode": f"{stat.S_IMODE(info.st_mode):04o}",
        # ELF validation intentionally consumes only this 64-byte header; the
        # rest of the descriptor stream is used solely for the binary hash.
        "elf": _elf_identity(header),
    }


def _load_prebinding() -> Any:
    path = Path(__file__).with_name("check_candidate_prebinding.py")
    spec = importlib.util.spec_from_file_location("phase3_candidate_prebinding", path)
    if spec is None or spec.loader is None:
        raise ReceiptError("cannot load Gate-A prebinding checker")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    # Always bind the freshly loaded checker to this module's seam.  A
    # receipt loaded by freeze has already received freeze's injected seam;
    # never rely on an ambient module or the checker's default by accident.
    module.GIT_EXECUTABLE = GIT_EXECUTABLE
    module.GIT_ENV = dict(GIT_ENV)
    return module


def capture_source_closure(repo: Path) -> dict[str, Any]:
    prebinding = _load_prebinding()
    try:
        base, current = prebinding.check(repo.resolve(), prebinding.BASE_COMMIT)
    except Exception as error:  # checker has its own fail-closed error type
        raise ReceiptError(f"Gate-A source closure check failed: {error}") from error
    if base != current:
        raise ReceiptError("Gate-A source closure changed during receipt capture")
    closure = {
        "algorithm": "ck.phase3-candidate-source-build-closure.v1",
        "base_commit": prebinding.BASE_COMMIT,
        "files": base.count,
        "bytes": base.total_bytes,
        "path_sha256": base.path_sha256,
        "content_sha256": base.content_sha256,
    }
    validate_source_closure(closure)
    return closure


def validate_source_closure(closure: Mapping[str, Any]) -> None:
    """Reject a receipt closure that is not the frozen Gate-A closure."""
    expected = {
        "algorithm": "ck.phase3-candidate-source-build-closure.v1",
        "base_commit": "f4125342211a1d1436ae48b685ec2342700f39c4",
        "files": 47,
        "bytes": 1_494_337,
        "path_sha256": "10605701d02f117ff7ef2756004fbf53a475eb92fbc0616e139f919d7a8480dc",
        "content_sha256": "21825e78c3286cf73d135f44be99eaea5214ce36b5fed6271dce096d364468e2",
    }
    if type(closure) is not dict or dict(closure) != expected:
        raise ReceiptError("source closure does not match the frozen Gate-A identity")


def _git_run(repo: Path, *arguments: str, **kwargs: Any) -> subprocess.CompletedProcess:
    kwargs.setdefault("check", False)
    kwargs["env"] = dict(GIT_ENV)
    return subprocess.run([GIT_EXECUTABLE, "-C", str(repo), *arguments], **kwargs)


def _git_head(repo: Path) -> str:
    result = _git_run(
        repo, "rev-parse", "--verify", "HEAD",
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode:
        raise ReceiptError(f"cannot resolve source commit: {result.stderr.strip()}")
    commit = result.stdout.strip()
    if not FULL_SHA_RE.fullmatch(commit):
        raise ReceiptError("repository HEAD is not a full commit SHA")
    status = _git_run(
        repo, "status", "--porcelain", "--untracked-files=all",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if status.returncode or status.stdout:
        raise ReceiptError("repository must be clean while capturing a build receipt")
    return commit


def _validate_platform_observation(value: Any) -> dict[str, Any]:
    expected = {"stability", "runner_os", "runner_arch", "image_os", "image_version", "kernel", "sanitized_environment_keys"}
    if type(value) is not dict or set(value) != expected:
        raise ReceiptError("platform_observation has an unexpected or missing field")
    for key in expected - {"sanitized_environment_keys"}:
        _string(value[key], f"platform_observation.{key}", max_bytes=1024)
    if value["sanitized_environment_keys"] != sorted(ENV_POLICY_VALUES):
        raise ReceiptError("platform_observation does not prove the exact sanitized environment")
    if value["stability"] != "observed-for-this-build-only":
        raise ReceiptError("platform_observation must not claim a stable hosted-image identity")
    return {key: value[key] for key in sorted(expected)}


def _validate_vendor_config(path: Path, vendor: Path) -> dict[str, Any]:
    """Validate the exact isolated Cargo source replacement used for vendoring."""
    raw, _ = _read_regular_file(path, "Cargo vendor config", max_bytes=MAX_METADATA_BYTES)
    config = _toml_document(raw, "Cargo vendor config", compatibility="vendor-config")
    expected = {
        "source": {
            "crates-io": {"replace-with": "vendored-sources"},
            "vendored-sources": {"directory": str(vendor.absolute())},
        }
    }
    if config != expected:
        raise ReceiptError("Cargo config is not the exact controlled vendor replacement")
    digest = hashlib.sha256(raw).hexdigest()
    return {"algorithm": "ck.exp-0002.phase3.gate-b-controlled-vendor-config.v1", "sha256": digest, "bytes": len(raw)}


def _validate_metadata(repo: Path, metadata: Mapping[str, Any]) -> dict[str, Any]:
    _exact_keys(metadata, {"schema", "source_commit", "candidate_profile_id", "platform_role", "target", "profile", "platform_observation", "build"}, "build metadata")
    if metadata["schema"] != METADATA_SCHEMA:
        raise ReceiptError("build metadata schema is not recognized")
    commit = _string(metadata["source_commit"], "source_commit")
    if not FULL_SHA_RE.fullmatch(commit):
        raise ReceiptError("source_commit must be a full lowercase SHA-1")
    role = _string(metadata["platform_role"], "platform_role")
    if metadata["candidate_profile_id"] != CANDIDATE_PROFILE_ID:
        raise ReceiptError("candidate_profile_id is not the frozen Gate-B profile")
    if role not in PLATFORM_ROLES:
        raise ReceiptError("platform_role is not recognized")
    if metadata["target"] != TARGET or metadata["profile"] != PROFILE:
        raise ReceiptError("target/profile are not the frozen Gate-B values")
    platform_observation = _validate_platform_observation(metadata["platform_observation"])

    build = metadata["build"]
    if type(build) is not dict:
        raise ReceiptError("build metadata build field must be an object")
    _exact_keys(build, {"argv", "cwd", "env_policy", "toolchain", "cargo_lock_path", "dependency_metadata_path", "vendor_path", "vendor_role_path", "binary_role_path", "cargo_config_path", "cargo_config_role_path"}, "build metadata build")
    argv = build["argv"]
    if type(argv) is not list or not argv or any(type(item) is not str or not item for item in argv):
        raise ReceiptError("build argv must be a non-empty string list")
    target_directory = argv[8] if len(argv) > 8 and argv[7] == "--target-dir" else ""
    expected_argv = ["cargo", f"+{TOOLCHAIN}", "build", "--manifest-path", CANDIDATE_MANIFEST, "--target", TARGET, "--target-dir", target_directory, "--locked", "--offline"]
    if len(argv) != len(expected_argv) or argv[:7] != expected_argv[:7] or argv[9:] != expected_argv[9:] or not target_directory or not Path(target_directory).is_absolute():
        raise ReceiptError("build argv is not the exact frozen offline dev build")
    cwd = _safe_relative(build["cwd"], "build.cwd") if build["cwd"] != "." else "."
    env_policy = build["env_policy"]
    if type(env_policy) is not dict:
        raise ReceiptError("build.env_policy must be an object")
    _exact_keys(env_policy, {"mode", "ambient", "variables"}, "build.env_policy")
    if env_policy["mode"] != "sanitized-env-i" or env_policy["ambient"] != "excluded" or type(env_policy["variables"]) is not dict:
        raise ReceiptError("build.env_policy must exclude ambient environment state")
    if env_policy["variables"] != ENV_POLICY_VALUES:
        raise ReceiptError("build.env_policy variables differ from the frozen allowlist")
    if any(type(key) is not str or type(value) is not str for key, value in env_policy["variables"].items()):
        raise ReceiptError("build.env_policy variables must be a string map")
    toolchain = build["toolchain"]
    if type(toolchain) is not dict:
        raise ReceiptError("build.toolchain must be an object")
    _exact_keys(toolchain, {"rust_toolchain", "rustc", "cargo", "python"}, "build.toolchain")
    if toolchain["rust_toolchain"] != TOOLCHAIN:
        raise ReceiptError("build toolchain is not Rust 1.97.1")
    for key in ("rustc", "cargo", "python"):
        _string(toolchain[key], f"build.toolchain.{key}")
    lock_path = _safe_relative(build["cargo_lock_path"], "build.cargo_lock_path")
    if lock_path != CANDIDATE_LOCK:
        raise ReceiptError("build.cargo_lock_path is not the standalone candidate lockfile")
    dependency_path = Path(_string(build["dependency_metadata_path"], "build.dependency_metadata_path"))
    if not dependency_path.is_absolute():
        dependency_path = repo / dependency_path
    _regular_file(dependency_path, "dependency metadata")
    lock_file = repo / lock_path
    _regular_file(lock_file, "Cargo.lock")
    binary_role_path = _safe_relative(build["binary_role_path"], "build.binary_role_path")
    vendor_role_path = _safe_relative(build["vendor_role_path"], "build.vendor_role_path")
    vendor_path = _safe_tree_root(Path(_string(build["vendor_path"], "build.vendor_path")), "vendor directory")
    config_path = Path(_string(build["cargo_config_path"], "build.cargo_config_path"))
    config_role_path = _safe_relative(build["cargo_config_role_path"], "build.cargo_config_role_path")
    config = _validate_vendor_config(config_path, vendor_path)
    lock_sha, lock_bytes = _sha256(lock_file, "Cargo.lock", max_bytes=MAX_METADATA_BYTES)
    dependency = _dependency_identity(dependency_path, repo, vendor=vendor_path, lock=lock_file)
    vendor = capture_vendor_closure(vendor_path)
    validate_vendor_closure(vendor)
    return {
        "platform_role": role,
        "platform_observation": platform_observation,
        "target": TARGET,
        "profile": PROFILE,
        "argv": list(argv),
        "cwd": cwd,
        "env_policy": env_policy,
        "toolchain": toolchain,
        "cargo_lock": {"path": lock_path, "sha256": lock_sha, "bytes": lock_bytes},
        "dependency_closure": dependency,
        "vendor_closure": {"role_path": vendor_role_path, **vendor},
        "cargo_config": {"role_path": config_role_path, **config},
        "binary_role_path": binary_role_path,
    }


def _stable_manifest_role(manifest_path: Any, repo: Path, label: str) -> str:
    """Normalize a path package's manifest to a repository-relative role."""
    raw = _string(manifest_path, label)
    if "\\" in raw:
        raise ReceiptError(f"{label} contains a Windows path separator")
    normalized = posixpath.normpath(raw)
    repo_root = repo.absolute().as_posix().rstrip("/")
    if normalized.startswith("/"):
        prefix = repo_root + "/"
        if not normalized.startswith(prefix):
            raise ReceiptError(f"{label} is outside the repository")
        normalized = normalized[len(prefix):]
    return _safe_relative(normalized, label)


def _validate_vendor_packages(vendor: Path, packages: list[dict[str, Any]], *, lock_registry: Mapping[tuple[str, str], str] | None = None) -> None:
    """Bind every vendored registry package to Cargo metadata identity."""
    expected: dict[tuple[str, str], str | None] = {}
    for package in packages:
        if package["source"] is None:
            continue
        checksum = package["checksum"]
        # Cargo metadata reports null for registry packages after the
        # crates.io source has been replaced with a directory vendor.  The
        # generated vendor checksum is validated below; a present metadata
        # checksum remains an independently checked cross-binding.
        if package["source"] != REGISTRY_SOURCE or (checksum is not None and (not isinstance(checksum, str) or not re.fullmatch(r"[0-9a-f]{64}", checksum))):
            raise ReceiptError("Cargo metadata contains a non-crates.io or unchecksummed dependency")
        identity = (package["name"], package["version"])
        if identity in expected:
            raise ReceiptError("Cargo metadata contains duplicate vendored package identity")
        expected[identity] = checksum

    actual: dict[tuple[str, str], str] = {}
    root = _safe_tree_root(vendor, "vendor directory")
    try:
        children = sorted(os.scandir(root), key=lambda item: item.name.encode("utf-8"))
    except OSError as error:
        raise ReceiptError(f"cannot scan vendor directory: {error}") from error
    for child in children:
        child_path = Path(child.path)
        try:
            info = child_path.lstat()
        except OSError as error:
            raise ReceiptError(f"cannot stat vendor package: {error}") from error
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise ReceiptError("vendor root contains an unrelated non-package entry")
        manifest = _toml_file(child_path / "Cargo.toml", f"vendor package {child.name} manifest")
        package = manifest.get("package")
        if type(package) is not dict or type(package.get("name")) is not str or type(package.get("version")) is not str:
            raise ReceiptError(f"vendor package {child.name} has no bounded package identity")
        identity = (package["name"], package["version"])
        if identity in actual:
            raise ReceiptError("vendor directory contains duplicate package identity")
        checksum = _json_file(child_path / ".cargo-checksum.json", f"vendor package {child.name} checksum")
        if set(checksum) not in ({"files", "package"}, {"$comment", "files", "package"}) or type(checksum["files"]) is not dict or type(checksum["package"]) is not str or not re.fullmatch(r"[0-9a-f]{64}", checksum["package"]):
            raise ReceiptError(f"vendor package {child.name} checksum record is malformed")
        if "$comment" in checksum and checksum["$comment"] != VENDOR_CHECKSUM_COMMENT:
            raise ReceiptError(f"vendor package {child.name} checksum record is malformed")
        _validate_vendor_file_map(child_path, checksum["files"], f"vendor package {child.name}")
        actual[identity] = checksum["package"]
    if set(actual) != set(expected):
        raise ReceiptError("vendored package identities do not exactly match Cargo metadata")
    if lock_registry is not None and set(actual) != set(lock_registry):
        raise ReceiptError("vendored package identities do not exactly match Cargo.lock")
    for identity, expected_checksum in expected.items():
        actual_checksum = actual[identity]
        lock_checksum = lock_registry.get(identity) if lock_registry is not None else None
        if expected_checksum is not None and actual_checksum != expected_checksum:
            raise ReceiptError("vendored package checksum differs from Cargo metadata")
        if lock_checksum is not None and actual_checksum != lock_checksum:
            raise ReceiptError("vendored package checksum differs from Cargo.lock")


def _toml_file(path: Path, label: str) -> dict[str, Any]:
    raw, _ = _read_regular_file(path, label, max_bytes=MAX_METADATA_BYTES)
    return _toml_document(raw, label, compatibility="package-manifest")


def _toml_basic_string(encoded: str, label: str, line_number: int) -> str:
    """Decode one TOML basic string for the Python 3.10 compatibility path."""
    decoder = json.JSONDecoder()
    try:
        value, end = decoder.raw_decode(encoded)
    except (json.JSONDecodeError, RecursionError) as error:
        raise ReceiptError(f"{label} has malformed TOML at line {line_number}") from error
    tail = encoded[end:].strip()
    if type(value) is not str or (tail and not tail.startswith("#")):
        raise ReceiptError(f"{label} has malformed TOML at line {line_number}")
    return value


def _compat_package_manifest(raw: bytes, label: str) -> dict[str, Any]:
    """Extract package identity on Python 3.10.

    Python 3.11+ always uses the complete stdlib parser.  The compatibility
    path deliberately ignores ordinary Cargo package keys and later tables,
    while strictly parsing the two identity strings needed by this receipt.
    """
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ReceiptError(f"{label} is not valid UTF-8 TOML") from error
    section: str | None = None
    package: dict[str, str] = {}
    for line_number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            section = stripped[1:-1].strip()
            continue
        if section != "package" or "=" not in stripped:
            continue
        key, encoded = (part.strip() for part in stripped.split("=", 1))
        if key not in {"name", "version"}:
            continue
        if key in package:
            raise ReceiptError(f"{label} has a duplicate package identity key")
        package[key] = _toml_basic_string(encoded, label, line_number)
    return {"package": package}


def _compat_vendor_config(raw: bytes, label: str) -> dict[str, Any]:
    """Parse the exact Cargo-generated source replacement on Python 3.10."""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ReceiptError(f"{label} is not valid UTF-8 TOML") from error
    allowed = {
        "source.crates-io": {"replace-with"},
        "source.vendored-sources": {"directory"},
    }
    flat: dict[str, dict[str, str]] = {}
    section: str | None = None
    for line_number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            section = stripped[1:-1].strip()
            if section not in allowed or section in flat:
                raise ReceiptError(f"{label} has an unexpected or duplicate TOML section")
            flat[section] = {}
            continue
        if section not in allowed or "=" not in stripped:
            raise ReceiptError(f"{label} has malformed TOML at line {line_number}")
        key, encoded = (part.strip() for part in stripped.split("=", 1))
        if key not in allowed[section] or key in flat[section]:
            raise ReceiptError(f"{label} has an unexpected or duplicate TOML key")
        flat[section][key] = _toml_basic_string(encoded, label, line_number)
    return {
        "source": {
            "crates-io": flat.get("source.crates-io", {}),
            "vendored-sources": flat.get("source.vendored-sources", {}),
        }
    }


def _compat_cargo_lock(raw: bytes, label: str) -> dict[str, Any]:
    """Parse the bounded Cargo.lock subset needed by the receipt on Python 3.10."""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ReceiptError(f"{label} is not valid UTF-8 TOML") from error
    version: int | None = None
    packages: list[dict[str, Any]] = []
    package: dict[str, Any] | None = None
    array_key: str | None = None
    array_values: list[str] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if array_key is not None:
            if stripped == "]":
                assert package is not None
                package[array_key] = array_values
                array_key = None
                array_values = []
                continue
            if not stripped.endswith(","):
                raise ReceiptError(f"{label} has malformed TOML at line {line_number}")
            array_values.append(_toml_basic_string(stripped[:-1].strip(), label, line_number))
            continue
        if not stripped or stripped.startswith("#"):
            continue
        if stripped == "[[package]]":
            if package is not None:
                packages.append(package)
            package = {}
            continue
        if stripped.startswith("["):
            raise ReceiptError(f"{label} has an unexpected TOML section at line {line_number}")
        if "=" not in stripped:
            raise ReceiptError(f"{label} has malformed TOML at line {line_number}")
        key, encoded = (part.strip() for part in stripped.split("=", 1))
        if package is None:
            if key != "version" or version is not None or not re.fullmatch(r"[0-9]+", encoded):
                raise ReceiptError(f"{label} has an unexpected top-level field at line {line_number}")
            version = int(encoded)
            continue
        if key in package or key not in {"name", "version", "source", "checksum", "dependencies"}:
            raise ReceiptError(f"{label} has an unexpected or duplicate package field at line {line_number}")
        if key == "dependencies":
            if encoded == "[]":
                package[key] = []
            elif encoded == "[":
                array_key = key
            else:
                raise ReceiptError(f"{label} has malformed dependency array at line {line_number}")
        else:
            package[key] = _toml_basic_string(encoded, label, line_number)
    if array_key is not None:
        raise ReceiptError(f"{label} has an unterminated dependency array")
    if package is not None:
        packages.append(package)
    if version is None or not packages:
        raise ReceiptError(f"{label} is missing its version or package records")
    return {"version": version, "package": packages}


def _toml_document(raw: bytes, label: str, *, compatibility: str) -> dict[str, Any]:
    """Parse bounded TOML with stdlib tomllib and a Python 3.10 fallback."""
    if tomllib is None:
        if compatibility == "package-manifest":
            return _compat_package_manifest(raw, label)
        if compatibility == "vendor-config":
            return _compat_vendor_config(raw, label)
        if compatibility == "cargo-lock":
            return _compat_cargo_lock(raw, label)
        raise ReceiptError(f"{label} has no Python 3.10 compatibility parser")
    try:
        value = tomllib.loads(raw.decode("utf-8"))
    except RecursionError as error:
        raise ReceiptError(f"{label} exceeds the bounded TOML nesting depth") from error
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise ReceiptError(f"{label} is not valid TOML: {error}") from error
    if type(value) is not dict:
        raise ReceiptError(f"{label} must be a TOML document")
    return value


def _cargo_lock_registry(path: Path) -> dict[tuple[str, str], str]:
    raw, _ = _read_regular_file(path, "Cargo.lock", max_bytes=MAX_METADATA_BYTES)
    lock = _toml_document(raw, "Cargo.lock", compatibility="cargo-lock")
    if set(lock) != {"version", "package"} or lock["version"] != 4 or type(lock["package"]) is not list:
        raise ReceiptError("Cargo.lock is not the exact version-4 package document")
    registry: dict[tuple[str, str], str] = {}
    for index, package in enumerate(lock["package"]):
        if type(package) is not dict:
            raise ReceiptError(f"Cargo.lock package {index} is malformed")
        if set(package) - {"name", "version", "source", "checksum", "dependencies"}:
            raise ReceiptError(f"Cargo.lock package {index} has unexpected fields")
        name = _string(package.get("name"), f"Cargo.lock package {index}.name")
        version = _string(package.get("version"), f"Cargo.lock package {index}.version")
        source = package.get("source")
        checksum = package.get("checksum")
        if source is None:
            if checksum is not None:
                raise ReceiptError(f"Cargo.lock package {index} path package has a checksum")
            continue
        _string(source, f"Cargo.lock package {index}.source")
        if source != REGISTRY_SOURCE:
            raise ReceiptError(f"Cargo.lock package {index} uses an unsupported source")
        if type(checksum) is not str or not re.fullmatch(r"[0-9a-f]{64}", checksum):
            raise ReceiptError(f"Cargo.lock package {index} checksum is malformed")
        identity = (name, version)
        if identity in registry:
            raise ReceiptError("Cargo.lock contains duplicate registry package identity")
        registry[identity] = checksum
    if not registry:
        raise ReceiptError("Cargo.lock contains no registry packages")
    return registry


def _vendor_relative(path: Any, label: str) -> str:
    value = _string(path, label)
    if "\\" in value or value.startswith("/") or "\x00" in value:
        raise ReceiptError(f"{label} is not a safe relative POSIX path")
    normalized = posixpath.normpath(value)
    if normalized != value or normalized in {"", ".", ".."} or normalized.startswith("../"):
        raise ReceiptError(f"{label} is not a normalized relative POSIX path")
    return normalized


def _validate_vendor_file_map(package: Path, files: Mapping[str, Any], label: str) -> None:
    expected: dict[str, str] = {}
    for raw_path, checksum in files.items():
        relative = _vendor_relative(raw_path, f"{label} file path")
        if relative in expected:
            raise ReceiptError(f"{label} contains duplicate file paths")
        if type(checksum) is not str or not re.fullmatch(r"[0-9a-f]{64}", checksum):
            raise ReceiptError(f"{label} file checksum is malformed")
        expected[relative] = checksum

    actual: dict[str, str] = {}
    stack = [package]
    while stack:
        directory = stack.pop()
        try:
            children = sorted(os.scandir(directory), key=lambda item: item.name.encode("utf-8"), reverse=True)
        except OSError as error:
            raise ReceiptError(f"cannot scan {label} files: {error}") from error
        for child in children:
            child_path = Path(child.path)
            try:
                info = child_path.lstat()
            except OSError as error:
                raise ReceiptError(f"cannot stat {label} file: {error}") from error
            if stat.S_ISLNK(info.st_mode):
                raise ReceiptError(f"{label} contains a symlink")
            if stat.S_ISDIR(info.st_mode):
                stack.append(child_path)
                continue
            if not stat.S_ISREG(info.st_mode):
                raise ReceiptError(f"{label} contains a non-regular file")
            relative = child_path.relative_to(package).as_posix()
            if relative == ".cargo-checksum.json":
                continue
            relative = _vendor_relative(relative, f"{label} actual file path")
            if relative in actual:
                raise ReceiptError(f"{label} contains duplicate actual file paths")
            digest, _ = _sha256(child_path, f"{label} file {relative}", max_bytes=MAX_VENDOR_FILE_BYTES)
            actual[relative] = digest
    if set(actual) != set(expected):
        raise ReceiptError(f"{label} file map does not cover the actual vendored files")
    for relative, expected_checksum in expected.items():
        if actual[relative] != expected_checksum:
            raise ReceiptError(f"{label} file checksum does not match the vendored file")


def _dependency_identity(path: Path, repo: Path, *, vendor: Path | None = None, lock: Path | None = None) -> dict[str, Any]:
    metadata = _json_file(path, "Cargo metadata")
    required = {"packages", "workspace_members", "workspace_default_members", "resolve", "workspace_root", "version"}
    if not required.issubset(metadata) or type(metadata["packages"]) is not list or type(metadata["workspace_members"]) is not list:
        raise ReceiptError("Cargo metadata lacks its resolved package closure")
    if metadata["version"] != 1:
        raise ReceiptError("Cargo metadata format version is not 1")
    workspace_root = _stable_manifest_role(str(metadata["workspace_root"]) + "/Cargo.toml", repo, "Cargo metadata workspace_root")
    if workspace_root != CANDIDATE_MANIFEST:
        raise ReceiptError("Cargo metadata is not for the standalone candidate workspace")
    resolve = metadata["resolve"]
    if type(resolve) is not dict or type(resolve.get("nodes")) is not list:
        raise ReceiptError("Cargo metadata resolve.nodes is missing")
    lock_registry = _cargo_lock_registry(lock) if lock is not None else None
    packages: list[dict[str, Any]] = []
    package_ids: set[str] = set()
    id_map: dict[str, str] = {}
    metadata_registry: dict[tuple[str, str], str | None] = {}
    for index, package in enumerate(metadata["packages"]):
        if type(package) is not dict:
            raise ReceiptError(f"Cargo metadata package {index} is malformed")
        for key in ("id", "name", "version"):
            _string(package.get(key), f"Cargo metadata package {index}.{key}")
        package_id = package["id"]
        if package_id in package_ids:
            raise ReceiptError("Cargo metadata contains duplicate package IDs")
        package_ids.add(package_id)
        source = package.get("source")
        if source is not None:
            _string(source, f"Cargo metadata package {index}.source")
        checksum = package.get("checksum")
        if checksum is not None:
            _string(checksum, f"Cargo metadata package {index}.checksum")
        manifest_role = None
        normalized_id = package_id
        if source is None:
            manifest_role = _stable_manifest_role(package.get("manifest_path"), repo, f"Cargo metadata package {index}.manifest_path")
            if manifest_role not in {CANDIDATE_MANIFEST, CORE_MANIFEST}:
                raise ReceiptError("Cargo metadata contains an unrelated path package")
            normalized_id = f"path+repo:{manifest_role}#{package['name']}@{package['version']}"
            if manifest_role == CANDIDATE_MANIFEST and (package["name"] != CANDIDATE_PACKAGE_NAME or package["version"] != CANDIDATE_PACKAGE_VERSION):
                raise ReceiptError("Cargo metadata candidate package identity is not the frozen package")
        elif source != REGISTRY_SOURCE:
            raise ReceiptError("Cargo metadata contains an unsupported dependency source")
        else:
            identity = (package["name"], package["version"])
            if checksum is not None and not re.fullmatch(r"[0-9a-f]{64}", checksum):
                raise ReceiptError("Cargo metadata registry package checksum is malformed")
            if lock_registry is not None:
                if identity not in lock_registry:
                    raise ReceiptError("Cargo metadata registry identity is missing from Cargo.lock")
                if checksum is not None and checksum != lock_registry[identity]:
                    raise ReceiptError("Cargo metadata registry checksum differs from Cargo.lock")
            if checksum is None and (vendor is None or lock_registry is None):
                raise ReceiptError("Cargo metadata registry checksum is absent without vendor and lock proof")
            if identity in metadata_registry:
                raise ReceiptError("Cargo metadata contains duplicate registry package identity")
            metadata_registry[identity] = checksum
        id_map[package_id] = normalized_id
        packages.append({"id": normalized_id, "name": package["name"], "version": package["version"], "source": source, "checksum": checksum, "manifest_role": manifest_role})
    if lock_registry is not None and set(metadata_registry) != set(lock_registry):
        raise ReceiptError("Cargo metadata registry identities do not exactly match Cargo.lock")
    nodes: list[dict[str, Any]] = []
    node_ids: set[str] = set()
    for index, node in enumerate(resolve["nodes"]):
        if type(node) is not dict or type(node.get("id")) is not str or type(node.get("dependencies")) is not list:
            raise ReceiptError(f"Cargo metadata resolve node {index} is malformed")
        node_id = node["id"]
        if node_id in node_ids or node_id not in package_ids:
            raise ReceiptError("Cargo metadata resolve node IDs are inconsistent")
        node_ids.add(node_id)
        dependencies = []
        for dependency in node["dependencies"]:
            _string(dependency, f"Cargo metadata resolve node {index}.dependency")
            if dependency not in package_ids:
                raise ReceiptError("Cargo metadata resolve dependency is not a package")
            dependencies.append(id_map[dependency])
        nodes.append({"id": id_map[node_id], "dependencies": sorted(set(dependencies))})
    raw_members = sorted({_string(item, "Cargo metadata workspace member") for item in metadata["workspace_members"]})
    if not set(raw_members).issubset(package_ids):
        raise ReceiptError("Cargo metadata workspace member is not a package")
    members = sorted(id_map[item] for item in raw_members)
    default_members = sorted({_string(item, "Cargo metadata workspace default member") for item in metadata["workspace_default_members"]})
    if default_members != raw_members:
        raise ReceiptError("Cargo metadata workspace is not the standalone candidate")
    candidate_ids = [raw_id for raw_id, normalized in id_map.items() if normalized == f"path+repo:{CANDIDATE_MANIFEST}#{CANDIDATE_PACKAGE_NAME}@{CANDIDATE_PACKAGE_VERSION}"]
    if len(candidate_ids) != 1 or raw_members != candidate_ids:
        raise ReceiptError("Cargo metadata workspace member is not the frozen candidate package")
    if resolve.get("root") != candidate_ids[0]:
        raise ReceiptError("Cargo metadata resolve root is not the candidate package")
    if node_ids != package_ids:
        raise ReceiptError("Cargo metadata resolved graph is incomplete")
    canonical = {"packages": sorted(packages, key=lambda item: item["id"]), "workspace_members": members, "nodes": sorted(nodes, key=lambda item: item["id"])}
    if vendor is not None:
        _validate_vendor_packages(vendor, [{"name": package["name"], "version": package["version"], "source": package["source"], "checksum": package["checksum"]} for package in packages], lock_registry=lock_registry)
    digest = hashlib.sha256(DEPENDENCY_HASH_DOMAIN + _canonical(canonical)).hexdigest()
    raw_sha, raw_bytes = _sha256(path)
    return {"schema": DEPENDENCY_SCHEMA, "algorithm": "ck.exp-0002.phase3.gate-b-dependency-closure.v1", "sha256": digest, "raw_sha256": raw_sha, "bytes": raw_bytes, "packages": len(packages), "nodes": len(nodes)}


def _validate_facts(receipt: Mapping[str, Any]) -> None:
    _exact_keys(receipt, {"schema", "phase_id", "candidate_profile_id", "mode", "execution_permitted", "source_commit", "source_closure", "build", "binary", "custody", "receipt_sha256"}, "receipt")
    if receipt["schema"] != RECEIPT_SCHEMA or receipt["phase_id"] != PHASE_ID or receipt["candidate_profile_id"] != CANDIDATE_PROFILE_ID or receipt["mode"] != "build-only" or receipt["execution_permitted"] is not False:
        raise ReceiptError("receipt has invalid fixed identity")
    if not FULL_SHA_RE.fullmatch(_string(receipt["source_commit"], "receipt.source_commit")):
        raise ReceiptError("receipt.source_commit is invalid")
    validate_source_closure(receipt["source_closure"])
    build = receipt["build"]
    if type(build) is not dict:
        raise ReceiptError("receipt.build is not an object")
    _exact_keys(build, {"platform_role", "platform_observation", "target", "profile", "argv", "cwd", "env_policy", "toolchain", "cargo_lock", "dependency_closure", "vendor_closure", "cargo_config", "binary_role_path"}, "receipt.build")
    if build["platform_role"] not in PLATFORM_ROLES or build["target"] != TARGET or build["profile"] != PROFILE:
        raise ReceiptError("receipt.build has an invalid platform, target, or profile")
    _validate_platform_observation(build["platform_observation"])
    if type(build["argv"]) is not list or not build["argv"] or any(type(item) is not str for item in build["argv"]):
        raise ReceiptError("receipt.build.argv is malformed")
    target_directory = build["argv"][8] if len(build["argv"]) > 8 and build["argv"][7] == "--target-dir" else ""
    expected_prefix = ["cargo", f"+{TOOLCHAIN}", "build", "--manifest-path", CANDIDATE_MANIFEST, "--target", TARGET]
    if len(build["argv"]) != 11 or build["argv"][:7] != expected_prefix or build["argv"][7:] != ["--target-dir", target_directory, "--locked", "--offline"] or not target_directory or not Path(target_directory).is_absolute():
        raise ReceiptError("receipt.build.argv is not the exact frozen offline dev build")
    if build["cwd"] != ".":
        raise ReceiptError("receipt.build.cwd is not the repository root")
    toolchain = build["toolchain"]
    if type(toolchain) is not dict:
        raise ReceiptError("receipt.build.toolchain is malformed")
    _exact_keys(toolchain, {"rust_toolchain", "rustc", "cargo", "python"}, "receipt.build.toolchain")
    if toolchain["rust_toolchain"] != TOOLCHAIN:
        raise ReceiptError("receipt.build.toolchain is not Rust 1.97.1")
    for key in ("rustc", "cargo", "python"):
        _string(toolchain[key], f"receipt.build.toolchain.{key}")
    env_policy = build["env_policy"]
    if type(env_policy) is not dict or set(env_policy) != {"mode", "ambient", "variables"} or env_policy["mode"] != "sanitized-env-i" or env_policy["ambient"] != "excluded" or type(env_policy["variables"]) is not dict:
        raise ReceiptError("receipt.build.env_policy is malformed")
    if env_policy["variables"] != ENV_POLICY_VALUES:
        raise ReceiptError("receipt.build.env_policy variables differ from the frozen allowlist")
    _safe_relative(build["binary_role_path"], "receipt.build.binary_role_path")
    lock = build["cargo_lock"]
    if type(lock) is not dict:
        raise ReceiptError("receipt.build.cargo_lock is malformed")
    _exact_keys(lock, {"path", "sha256", "bytes"}, "receipt.build.cargo_lock")
    _safe_relative(lock["path"], "receipt.build.cargo_lock.path")
    if lock["path"] != CANDIDATE_LOCK:
        raise ReceiptError("receipt.build.cargo_lock.path is not the standalone candidate lockfile")
    if not isinstance(lock["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", lock["sha256"]):
        raise ReceiptError("receipt.build.cargo_lock.sha256 is malformed")
    if type(lock["bytes"]) is not int or lock["bytes"] <= 0:
        raise ReceiptError("receipt.build.cargo_lock.bytes is malformed")
    dependency = build["dependency_closure"]
    if type(dependency) is not dict:
        raise ReceiptError("receipt.build.dependency_closure is malformed")
    _exact_keys(dependency, {"schema", "algorithm", "sha256", "raw_sha256", "bytes", "packages", "nodes"}, "receipt.build.dependency_closure")
    if dependency["schema"] != DEPENDENCY_SCHEMA or dependency["algorithm"] != "ck.exp-0002.phase3.gate-b-dependency-closure.v1":
        raise ReceiptError("receipt dependency closure schema is invalid")
    for key in ("sha256", "raw_sha256"):
        if not isinstance(dependency[key], str) or not re.fullmatch(r"[0-9a-f]{64}", dependency[key]):
            raise ReceiptError(f"receipt dependency closure {key} is malformed")
    for key in ("bytes", "packages", "nodes"):
        if type(dependency[key]) is not int or dependency[key] < 0:
            raise ReceiptError(f"receipt dependency closure {key} is malformed")
    vendor = build["vendor_closure"]
    if type(vendor) is not dict:
        raise ReceiptError("receipt.build.vendor_closure is malformed")
    _exact_keys(vendor, {"role_path", "algorithm", "files", "bytes", "path_sha256", "content_sha256"}, "receipt.build.vendor_closure")
    vendor_role_path = vendor.get("role_path")
    _safe_relative(vendor_role_path, "receipt.build.vendor_closure.role_path")
    validate_vendor_closure({key: vendor.get(key) for key in ("algorithm", "files", "bytes", "path_sha256", "content_sha256")})
    config = build["cargo_config"]
    if type(config) is not dict:
        raise ReceiptError("receipt.build.cargo_config is malformed")
    _exact_keys(config, {"role_path", "algorithm", "sha256", "bytes"}, "receipt.build.cargo_config")
    _safe_relative(config["role_path"], "receipt.build.cargo_config.role_path")
    if config["algorithm"] != "ck.exp-0002.phase3.gate-b-controlled-vendor-config.v1" or not isinstance(config["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", config["sha256"]) or type(config["bytes"]) is not int or config["bytes"] <= 0:
        raise ReceiptError("receipt.build.cargo_config identity is malformed")
    binary = receipt["binary"]
    if type(binary) is not dict:
        raise ReceiptError("receipt.binary is not an object")
    _exact_keys(binary, {"role", "path", "sha256", "bytes", "mode", "elf"}, "receipt.binary")
    if binary["role"] != "phase3-candidate":
        raise ReceiptError("receipt.binary.role is invalid")
    _safe_relative(binary["path"], "receipt.binary.path")
    if not isinstance(binary["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", binary["sha256"]):
        raise ReceiptError("receipt.binary.sha256 is malformed")
    if type(binary["bytes"]) is not int or binary["bytes"] <= 0:
        raise ReceiptError("receipt.binary.bytes is malformed")
    if type(binary["mode"]) is not str or not re.fullmatch(r"[0-7]{4,6}", binary["mode"]):
        raise ReceiptError("receipt.binary.mode is malformed")
    try:
        if not stat.S_ISREG(stat.S_IFREG | int(binary["mode"], 8)) or not (int(binary["mode"], 8) & 0o111):
            raise ReceiptError("receipt.binary.mode is not an executable regular-file mode")
    except ValueError as error:
        raise ReceiptError("receipt.binary.mode is malformed") from error
    elf = binary["elf"]
    if type(elf) is not dict:
        raise ReceiptError("receipt.binary.elf is malformed")
    _exact_keys(elf, {"class", "data", "machine", "type", "osabi", "entry_point"}, "receipt.binary.elf")
    if elf["class"] != "ELF64" or elf["data"] != "little-endian" or elf["machine"] != "x86_64" or elf["type"] not in {"ET_EXEC", "ET_DYN"}:
        raise ReceiptError("receipt.binary.elf identity is invalid")
    if type(elf["osabi"]) is not int or not 0 <= elf["osabi"] <= 255 or type(elf["entry_point"]) is not str:
        raise ReceiptError("receipt.binary.elf metadata is malformed")
    if receipt["custody"] != {"state": "transfer-only", "candidate_execution": "prohibited", "experiment_dispatch": "prohibited", "receipt_capture": "read-only"}:
        raise ReceiptError("receipt custody state is invalid")


def build_receipt(*, source_commit: str, source_closure: Mapping[str, Any], build: Mapping[str, Any], binary: Mapping[str, Any]) -> bytes:
    receipt: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "phase_id": PHASE_ID,
        "candidate_profile_id": CANDIDATE_PROFILE_ID,
        "mode": "build-only",
        "execution_permitted": False,
        "source_commit": source_commit,
        "source_closure": dict(source_closure),
        "build": dict(build),
        "binary": dict(binary),
        "custody": {"state": "transfer-only", "candidate_execution": "prohibited", "experiment_dispatch": "prohibited", "receipt_capture": "read-only"},
        "receipt_sha256": None,
    }
    _validate_facts(receipt)
    receipt["receipt_sha256"] = hashlib.sha256(SELF_HASH_DOMAIN + _canonical(receipt)).hexdigest()
    raw = _canonical(receipt)
    if len(raw) > MAX_RECEIPT_BYTES:
        raise ReceiptError("receipt exceeds the bounded receipt size")
    return raw + b"\n"


def validate_receipt(raw: bytes) -> dict[str, Any]:
    if not isinstance(raw, bytes) or len(raw) > MAX_RECEIPT_BYTES:
        raise ReceiptError("receipt is missing or too large")
    try:
        receipt = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicate_pairs)
    except RecursionError as error:
        raise ReceiptError("receipt exceeds the bounded JSON nesting depth") from error
    except (UnicodeDecodeError, json.JSONDecodeError, ReceiptError) as error:
        raise ReceiptError(f"receipt is invalid JSON: {error}") from error
    if type(receipt) is not dict:
        raise ReceiptError("receipt is not an object")
    _validate_facts(receipt)
    claimed = receipt["receipt_sha256"]
    if not isinstance(claimed, str) or not re.fullmatch(r"[0-9a-f]{64}", claimed):
        raise ReceiptError("receipt self-hash is malformed")
    unsigned = dict(receipt)
    unsigned["receipt_sha256"] = None
    expected = hashlib.sha256(SELF_HASH_DOMAIN + _canonical(unsigned)).hexdigest()
    if claimed != expected:
        raise ReceiptError("receipt self-hash does not match canonical contents")
    if raw != _canonical(receipt) + b"\n":
        raise ReceiptError("receipt bytes are not the exact canonical JSON representation")
    return receipt


def capture_receipt(repo: Path, binary: Path, metadata_path: Path, *, closure_capture: Callable[[Path], dict[str, Any]] = capture_source_closure) -> bytes:
    repo = repo.resolve()
    commit = _git_head(repo)
    metadata = _json_file(metadata_path, "build metadata")
    if metadata.get("source_commit") != commit:
        raise ReceiptError("build metadata source_commit differs from repository HEAD")
    closure = closure_capture(repo)
    validate_source_closure(closure)
    build = _validate_metadata(repo, metadata)
    binary_identity = capture_binary(repo, binary, recorded_path=build["binary_role_path"])
    return build_receipt(source_commit=commit, source_closure=closure, build=build, binary=binary_identity)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="capture a non-executing Phase 3 Gate-B build receipt")
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[4])
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        raw = capture_receipt(args.repo, args.binary, args.metadata)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(raw)
        validate_receipt(raw)
    except (OSError, ReceiptError) as error:
        print(f"PHASE3 BUILD RECEIPT FAILED: {error}", file=sys.stderr)
        return 1
    print(f"PHASE3 BUILD RECEIPT OK: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

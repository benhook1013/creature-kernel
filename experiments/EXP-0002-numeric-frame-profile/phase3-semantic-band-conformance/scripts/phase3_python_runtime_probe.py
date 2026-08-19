#!/usr/bin/env python3
"""Build-only CPython runtime attestation for the Phase 3 exact launcher.

The probe is a provenance tool, not an execution authority.  It prepares a
closed stdlib/native import set, records the prepared module and loader state,
and hashes bounded runtime files through descriptor-anchored, no-follow
opens.  Phase 3 sibling modules are deliberately not imported here: they are
authenticated separately by the launcher and freeze manifest.
"""

from __future__ import annotations

import argparse
import ast
import ctypes
import hashlib
import importlib
import json
import os
from pathlib import Path
import stat
import sys
import sysconfig
from typing import Any, Mapping


SCHEMA = "ck.exp-0002.phase3.python-runtime-attestation-1"
HASH_DOMAIN = b"ck.exp-0002.phase3.python-runtime-attestation.v1\0"
CONTRACT_SCHEMA = "ck.exp-0002.phase3.python-runtime-contract-2"
VERSION = "3.13.15"
IMPLEMENTATION = "CPython"
MODULE_LOADING = "explicit-sibling-file-loading-under-isolated-mode"
ENTRYPOINT = "phase3_exact_attempt_launcher.main->phase3_exact_attempt.run_exact_attempt"
LAUNCHER_RELATIVE = "scripts/phase3_exact_attempt_launcher.py"
SELECTORS = ("wsl2-x86_64", "ubuntu-24.04-x86_64")
ATTESTATION_PATHS = {
    "wsl2-x86_64": "manifests/runtime-attestations/wsl.json",
    "ubuntu-24.04-x86_64": "manifests/runtime-attestations/native.json",
}
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_FILES = 4096
MAX_MODULES = 4096
MAX_TOTAL_BYTES = 512 * 1024 * 1024
MAX_PATH_BYTES = 4096
MAX_MAP_BYTES = 16 * 1024 * 1024
SHA_HEX = set("0123456789abcdef")
IDENTITY_KEYS = frozenset({"path", "mode", "bytes", "sha256", "uid", "gid", "nlink"})
LEGACY_IDENTITY_KEYS = frozenset({"path", "mode", "bytes", "sha256"})

# These are the authenticated runtime and exact tool sets used by the
# launcher.  The receipt/freeze validators, their candidate-prebinding helper,
# and this probe are the provenance siblings loaded before/during an exact
# attempt; provenance generators and the experiment-closure tool remain
# separately frozen and are not imported here.
FROZEN_PHASE3_RUNTIME_SCRIPT_FILES = (
    "scripts/phase3_common.py",
    "scripts/phase3_oracle.py",
    "scripts/phase3_scorer.py",
    "scripts/phase3_runner.py",
    "scripts/phase3_receipt.py",
    "scripts/phase3_materialized_adapter.py",
    "scripts/phase3_evidence_contract.py",
    "scripts/phase3_gate_b_preflight.py",
)
FROZEN_PHASE3_EXACT_SCRIPT_FILES = (
    "scripts/phase3_exact_adjudicator.py",
    "scripts/phase3_exact_authority.py",
    "scripts/phase3_exact_custody.py",
    "scripts/phase3_exact_fp_observer.py",
    "scripts/phase3_exact_publication.py",
    "scripts/phase3_exact_transport.py",
    "scripts/phase3_exact_attempt.py",
    "scripts/phase3_exact_attempt_launcher.py",
)
FROZEN_PHASE3_RUNTIME_LOADED_PROVENANCE_FILES = (
    "scripts/phase3_build_receipt.py",
    "scripts/phase3_freeze_manifest.py",
    "scripts/check_candidate_prebinding.py",
    "scripts/phase3_python_runtime_probe.py",
)
FROZEN_PHASE3_SCRIPT_FILES = (
    *FROZEN_PHASE3_RUNTIME_SCRIPT_FILES,
    *FROZEN_PHASE3_EXACT_SCRIPT_FILES,
    *FROZEN_PHASE3_RUNTIME_LOADED_PROVENANCE_FILES,
)
FROZEN_PHASE3_LOCAL_MODULES = frozenset(Path(item).stem for item in FROZEN_PHASE3_SCRIPT_FILES) | {
    "phase3_python_runtime_probe",
}

# Direct imports found by the frozen source graph.  The native additions are
# explicit because several stdlib modules load them indirectly, and ctypes' C
# library handle is part of the fp-observer loader closure.
FROZEN_PHASE3_STDLIB_MODULES = (
    "argparse",
    "ast",
    "array",
    "base64",
    "binascii",
    "collections.abc",
    "ctypes",
    "dataclasses",
    "datetime",
    "decimal",
    "errno",
    "fcntl",
    "fractions",
    "hashlib",
    "importlib",
    "importlib.util",
    "inspect",
    "io",
    "json",
    "math",
    "os",
    "pathlib",
    "platform",
    "posixpath",
    "pwd",
    "re",
    "resource",
    "select",
    "selectors",
    "signal",
    "stat",
    "struct",
    "subprocess",
    "sys",
    "sysconfig",
    "tarfile",
    "tempfile",
    "threading",
    "time",
    "tomllib",
    "types",
    "typing",
    "zipfile",
    # Native modules used by the fixed CPython stdlib graph.
    "_ctypes",
    "_datetime",
    "_decimal",
    "_json",
    "_posixsubprocess",
    "_struct",
    "zlib",
)
FROZEN_PHASE3_STDLIB_TOP_LEVEL = frozenset(item.split(".", 1)[0] for item in FROZEN_PHASE3_STDLIB_MODULES)


class RuntimeProbeError(ValueError):
    """Stable fail-closed probe/attestation error."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = str(code)
        self.detail = str(detail).replace("\x00", "?").replace("\n", " ").replace("\r", "")[:512]
        super().__init__(f"{self.code}: {self.detail}" if self.detail else self.code)


def _fail(code: str, detail: str = "") -> None:
    raise RuntimeProbeError(code, detail)


def canonical(value: Any) -> bytes:
    try:
        return (json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise RuntimeProbeError("canonical-json", "value cannot be represented as canonical JSON") from error


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _path(value: Any, label: str, *, absolute: bool = True) -> str:
    if type(value) is not str or not value or "\x00" in value or "\\" in value:
        _fail("path", f"{label} is not a safe path")
    path = Path(value)
    if absolute and not path.is_absolute():
        _fail("path", f"{label} must be absolute")
    if any(part in {"", ".", ".."} for part in path.parts):
        _fail("path", f"{label} contains an unsafe component")
    try:
        if len(os.fsencode(value)) > MAX_PATH_BYTES:
            _fail("path", f"{label} exceeds the path bound")
    except UnicodeEncodeError as error:
        raise RuntimeProbeError("path", f"{label} is not encodable") from error
    return value


def _safe_mode(mode: Any, label: str, *, executable: bool = False) -> int:
    if type(mode) is not int or mode < 0 or mode > 0o7777 or mode & 0o022:
        _fail("file-mode", f"{label} is group/world writable or malformed")
    # The type bits are not part of the serialized mode, but retaining this
    # check makes accidental full st_mode declarations fail closed.
    if mode & stat.S_IFMT(mode):
        _fail("file-mode", f"{label} contains file type bits")
    if executable and not (mode & 0o111):
        _fail("file-mode", f"{label} is not executable")
    return mode


def _identity_shape(value: Any, label: str, *, executable: bool = False) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) not in {IDENTITY_KEYS, LEGACY_IDENTITY_KEYS}:
        _fail("identity-shape", f"{label} identity fields are not closed")
    _path(value["path"], f"{label}.path")
    _safe_mode(value["mode"], f"{label}.mode", executable=executable)
    if type(value["bytes"]) is not int or value["bytes"] < 0 or value["bytes"] > MAX_FILE_BYTES:
        _fail("file-size", f"{label}.bytes is outside the bound")
    if set(value) == IDENTITY_KEYS:
        for field in ("uid", "gid"):
            if type(value[field]) is not int or value[field] < 0 or value[field] > 0xFFFFFFFF:
                _fail("identity-shape", f"{label}.{field} is malformed")
        if type(value["nlink"]) is not int or value["nlink"] != 1:
            _fail("file-type", f"{label} is not a single-link file")
    if not isinstance(value["sha256"], str) or len(value["sha256"]) != 64 or any(c not in SHA_HEX for c in value["sha256"]):
        _fail("identity-shape", f"{label}.sha256 is malformed")
    return dict(value)


def _open_anchored_parent(path: Path, label: str) -> tuple[int, str]:
    """Walk every parent component with O_NOFOLLOW from the filesystem root."""
    if not getattr(os, "O_NOFOLLOW", 0):
        _fail("platform", "O_NOFOLLOW is required for runtime identity reads")
    raw_path = Path(os.fspath(path))
    if not raw_path.is_absolute() or len(raw_path.parts) < 2 or any(part in {"", ".", ".."} for part in raw_path.parts[1:]):
        _fail("path", f"{label} is not a canonical absolute path")
    absolute = Path(os.path.abspath(os.fspath(raw_path)))
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | os.O_NOFOLLOW
    parent = -1
    try:
        parent = os.open(os.sep, flags)
        for component in absolute.parts[1:-1]:
            child = os.open(component, flags, dir_fd=parent)
            if not stat.S_ISDIR(os.fstat(child).st_mode):
                os.close(child)
                _fail("path", f"{label} contains a non-directory parent")
            os.close(parent)
            parent = child
        return parent, absolute.parts[-1]
    except OSError as error:
        if parent >= 0:
            os.close(parent)
        if getattr(error, "errno", None) in {getattr(os, "ELOOP", 40), 40}:
            raise RuntimeProbeError("symlink", f"{label} contains a symlink component") from error
        raise RuntimeProbeError("missing-file", f"cannot open {label}") from error


def _read_fd(fd: int, size: int, label: str, *, limit: int = MAX_FILE_BYTES) -> bytes:
    if size < 0 or size > limit:
        _fail("file-size", f"{label} exceeds the bounded identity size")
    chunks: list[bytes] = []
    remaining = size
    while remaining:
        try:
            chunk = os.read(fd, min(1024 * 1024, remaining))
        except OSError as error:
            raise RuntimeProbeError("file-read", f"cannot read {label}") from error
        if not chunk:
            _fail("file-race", f"{label} ended before its declared size")
        chunks.append(chunk)
        remaining -= len(chunk)
        if remaining < 0:
            _fail("file-race", f"{label} grew while being read")
    return b"".join(chunks)


def _stat_signature(info: os.stat_result) -> tuple[int, int, int, int, int, int, int]:
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid, info.st_nlink, info.st_size)


def _identity(path: Path, *, root: Path | None = None, executable: bool = False) -> dict[str, Any]:
    """Read one file with descriptor anchoring and pre/during/post checks."""
    parent, name = _open_anchored_parent(path, str(path))
    fd = -1
    try:
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | os.O_NOFOLLOW
        try:
            fd = os.open(name, flags, dir_fd=parent)
        except OSError as error:
            if getattr(error, "errno", None) in {getattr(os, "ELOOP", 40), 40}:
                raise RuntimeProbeError("symlink", f"{path} is a symlink") from error
            raise RuntimeProbeError("missing-file", str(path)) from error
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            _fail("file-type", f"{path} is not a single-link regular file")
        mode = stat.S_IMODE(before.st_mode)
        _safe_mode(mode, str(path), executable=executable)
        if before.st_size < 0 or before.st_size > MAX_FILE_BYTES:
            _fail("file-size", f"{path} exceeds the bounded identity size")
        raw = _read_fd(fd, before.st_size, str(path))
        after = os.fstat(fd)
        if _stat_signature(before) != _stat_signature(after) or len(raw) != before.st_size:
            _fail("file-race", f"{path} changed while being read")
    finally:
        if fd >= 0:
            os.close(fd)
        os.close(parent)
    displayed = Path(os.path.abspath(os.fspath(path))).as_posix()
    if root is not None:
        try:
            displayed = Path(displayed).relative_to(Path(os.path.abspath(os.fspath(root)))).as_posix()
        except ValueError:
            _fail("runtime-root", f"{path} escaped the runtime root")
    return {
        "path": displayed,
        "mode": mode,
        "bytes": len(raw),
        "sha256": _sha(raw),
        "uid": int(before.st_uid),
        "gid": int(before.st_gid),
        "nlink": int(before.st_nlink),
    }


def _read_anchored(path: Path, label: str, *, limit: int = MAX_MAP_BYTES) -> bytes:
    """Read a bounded non-identity file (currently only /proc/self/maps)."""
    parent, name = _open_anchored_parent(path, label)
    fd = -1
    try:
        try:
            fd = os.open(name, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | os.O_NOFOLLOW, dir_fd=parent)
        except OSError as error:
            raise RuntimeProbeError("loader", f"cannot open {label}") from error
        before = os.fstat(fd)
        chunks: list[bytes] = []
        total = 0
        while total <= limit:
            try:
                chunk = os.read(fd, min(1024 * 1024, limit - total + 1))
            except OSError as error:
                raise RuntimeProbeError("loader", f"cannot read {label}") from error
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > limit:
                _fail("loader", f"{label} exceeds the bound")
        after = os.fstat(fd)
        if _stat_signature(before) != _stat_signature(after) and before.st_size != 0:
            _fail("loader-race", f"{label} changed while being read")
        return b"".join(chunks)
    finally:
        if fd >= 0:
            os.close(fd)
        os.close(parent)


def _file_allowed(path: Path) -> bool:
    name = path.name
    if any(part.endswith((".dist-info", ".egg-info")) for part in path.parts):
        return False
    # Cached bytecode is added only for modules whose __cached__ path is
    # actually observed.  The directory sweep remains source/native-only.
    if any(part == "__pycache__" for part in path.parts) or path.suffix in {".pyc", ".pyo"}:
        return False
    return path.suffix in {".py", ".so", ".dylib", ".dll", ".pyd"} or name.startswith("libpython")


def _is_under(path: Path, root: Path) -> bool:
    try:
        Path(os.path.abspath(os.fspath(path))).relative_to(Path(os.path.abspath(os.fspath(root))))
        return True
    except ValueError:
        return False


def _runtime_files(prefixes: list[Path], roots: list[Path]) -> list[dict[str, Any]]:
    paths: set[Path] = set()
    for root in roots:
        if not root.is_absolute() or not any(_is_under(root, prefix) or _is_under(prefix, root) for prefix in prefixes):
            continue
        for directory, dirnames, filenames in os.walk(root, followlinks=False):
            dirnames[:] = sorted(name for name in dirnames if name != "__pycache__" and not name.endswith((".dist-info", ".egg-info")))
            for name in sorted(filenames):
                path = Path(directory) / name
                if _file_allowed(path) and not path.is_symlink():
                    paths.add(path)
                    if len(paths) > MAX_FILES:
                        _fail("runtime-bound", "runtime file count exceeds the bound")
    result: list[dict[str, Any]] = []
    for path in sorted(paths, key=lambda item: os.fsencode(os.path.abspath(os.fspath(item)))):
        result.append(_identity(path))
    return result


def _local_origin(path: Path) -> bool:
    scripts = Path(os.path.abspath(os.path.dirname(__file__)))
    return _is_under(path, scripts)


def _module_origin(module: Any, name: str) -> dict[str, Any] | None:
    origin = getattr(module, "__file__", None)
    if origin is None:
        return None
    try:
        origin_path = Path(os.path.abspath(os.fspath(origin)))
    except (TypeError, ValueError):
        _fail("module", f"loaded module {name} has an invalid origin")
    if _local_origin(origin_path) or name.split(".", 1)[0] in FROZEN_PHASE3_LOCAL_MODULES:
        return None
    return _identity(origin_path)


def _cached_origin(module: Any, name: str) -> dict[str, Any] | None:
    cached = getattr(module, "__cached__", None)
    if not cached:
        return None
    try:
        cached_path = Path(os.path.abspath(os.fspath(cached)))
    except (TypeError, ValueError):
        _fail("bytecode-policy", f"loaded module {name} has an invalid __cached__ path")
    if _local_origin(cached_path) or name.split(".", 1)[0] in FROZEN_PHASE3_LOCAL_MODULES:
        return None
    try:
        return _identity(cached_path)
    except RuntimeProbeError as error:
        if error.code == "missing-file":
            return None
        raise


def _loaded_modules() -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for name, module in sorted(sys.modules.items(), key=lambda item: item[0].encode("utf-8") if isinstance(item[0], str) else b"\xff"):
        if not isinstance(name, str) or not name or module is None:
            continue
        origin = _module_origin(module, name)
        cached = _cached_origin(module, name)
        if origin is None and cached is None and getattr(module, "__file__", None) is not None:
            # A local sibling was intentionally omitted; malformed foreign
            # origins are not silently converted into an unbound module.
            if not (_local_origin(Path(os.path.abspath(os.fspath(getattr(module, "__file__"))))) or name.split(".", 1)[0] in FROZEN_PHASE3_LOCAL_MODULES):
                _fail("module", f"loaded module {name} has no readable origin")
        if origin is None and cached is None and getattr(module, "__file__", None) is not None:
            continue
        kind = "built-in" if origin is None and name in sys.builtin_module_names else ("extension" if origin is not None and Path(origin["path"]).suffix in {".so", ".dylib", ".dll", ".pyd"} else "source")
        result.append({"name": name, "kind": kind, "origin": origin, "cached": cached})
    result.sort(key=lambda item: item["name"].encode("utf-8"))
    return result


def _loader_objects() -> list[dict[str, Any]]:
    # ``/proc/self`` is a procfs magic symlink.  Resolve only its stable PID
    # spelling so the same anchored O_NOFOLLOW walk can be used for maps.
    maps = Path(f"/proc/{os.getpid()}/maps")
    if not maps.is_absolute():
        return []
    found: dict[str, dict[str, Any]] = {}
    try:
        lines = _read_anchored(maps, "/proc/self/maps").decode("ascii").splitlines()
    except (UnicodeDecodeError, RuntimeProbeError) as error:
        if isinstance(error, RuntimeProbeError) and error.code == "missing-file":
            return []
        if isinstance(error, RuntimeProbeError):
            raise
        raise RuntimeProbeError("loader", "loader map is not ASCII") from error
    for line in lines:
        fields = line.split()
        if len(fields) < 6:
            continue
        candidate = fields[-1]
        if not candidate.startswith("/") or candidate.startswith("/dev/") or candidate.endswith(" (deleted)"):
            continue
        path = Path(candidate)
        try:
            identity = _identity(path)
        except RuntimeProbeError as error:
            if error.code == "missing-file":
                _fail("loader", f"mapped loader disappeared: {path}")
            raise
        found[identity["path"]] = identity
        if len(found) > MAX_FILES:
            _fail("loader", "dynamic loader dependency count exceeds the bound")
    return [found[key] for key in sorted(found, key=lambda item: item.encode("utf-8"))]


def _environment_policy() -> dict[str, Any]:
    keys = sorted(key for key in os.environ if key in {"PATH", "HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "PYTHONPATH", "PYTHONHOME", "PYTHONNOUSERSITE", "PYTHONSAFEPATH", "LANG", "LC_ALL"})
    return {
        "mode": "sanitized-env-i",
        "ambient": "excluded",
        "observed_keys": keys,
        "values": {"PATH": "<bound-tool-path>", "HOME": "<sanitized-home>", "XDG_CONFIG_HOME": "<sanitized-xdg-config>", "XDG_CACHE_HOME": "<sanitized-cache>", "PYTHONPATH": "<forbidden>", "PYTHONHOME": "<forbidden>", "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1", "LANG": "C", "LC_ALL": "C"},
    }


def _record_hash(unsigned: Mapping[str, Any]) -> str:
    return _sha(HASH_DOMAIN + canonical(unsigned))


def _static_imports(source: bytes, filename: str = "<phase3-script>") -> tuple[set[str], set[str]]:
    """Return (stdlib, local/other) imports from one frozen source file."""
    try:
        tree = ast.parse(source.decode("utf-8"), filename=filename)
    except (UnicodeDecodeError, SyntaxError) as error:
        raise RuntimeProbeError("import-graph", f"cannot parse {filename}") from error
    stdlib: set[str] = set()
    other: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names = [node.module]
        else:
            continue
        for name in names:
            top = name.split(".", 1)[0]
            if top == "__future__":
                continue
            (stdlib if top in FROZEN_PHASE3_STDLIB_TOP_LEVEL or top in getattr(sys, "stdlib_module_names", ()) else other).add(name)
    return stdlib, other


def prepare_runtime_import_closure() -> tuple[str, ...]:
    """Import the fixed stdlib/native graph before runtime capture/validation.

    No sibling is imported here.  Importing libc via ctypes makes the native
    dependency used by the fixed fp observer visible in ``/proc/self/maps``.
    """
    prepared: list[str] = []
    for module_name in FROZEN_PHASE3_STDLIB_MODULES:
        try:
            importlib.import_module(module_name)
        except ModuleNotFoundError as error:
            # CPython 3.10 is retained as a test/inspection host and has no
            # stdlib tomllib.  The target 3.13 runtime must provide it; do
            # not report a skipped host import as prepared.
            if module_name == "tomllib" and tuple(sys.version_info[:2]) < (3, 11):
                continue
            raise RuntimeProbeError("import-closure", f"cannot prepare {module_name}") from error
        except (ImportError, OSError, RuntimeError) as error:
            raise RuntimeProbeError("import-closure", f"cannot prepare {module_name}") from error
        prepared.append(module_name)
    try:
        ctypes.CDLL(None, use_errno=True)
    except OSError as error:
        raise RuntimeProbeError("import-closure", "cannot prepare the fp-observer libc handle") from error
    # CPython may write a cache when importing a source module.  Existing
    # caches are not declared irrelevant: _loaded_modules records __cached__
    # identities whenever they exist.
    return tuple(prepared)


def _runtime_state() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    prepare_runtime_import_closure()
    return _loaded_modules(), _loader_objects()


def _canonical_identity_list(value: Any, label: str, *, executable: bool = False) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) > MAX_FILES:
        _fail("attestation-shape", f"{label} is malformed or exceeds the count bound")
    result = [_identity_shape(item, f"{label}[{index}]", executable=executable) for index, item in enumerate(value)]
    paths = [item["path"] for item in result]
    encoded = [path.encode("utf-8") for path in paths]
    if encoded != sorted(encoded) or len(paths) != len(set(paths)):
        _fail("attestation-shape", f"{label} is not canonically ordered or contains duplicates")
    return result


def _record_shape(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        _fail("attestation-shape", "runtime attestation must be an object")
    keys = {"schema", "selector", "implementation", "version", "interpreter", "interpreter_identity", "invocation", "module_loading", "entrypoint", "runtime_roots", "files", "imported_modules", "loader_dependencies", "sys_path", "environment_policy", "canonicalization", "attestation_sha256"}
    if set(value) != keys:
        _fail("attestation-shape", "runtime attestation fields are not closed")
    if value["schema"] != SCHEMA or value["selector"] not in SELECTORS or value["implementation"] != IMPLEMENTATION or value["version"] != VERSION:
        _fail("attestation-shape", "runtime attestation selector/version is wrong")
    _path(value["interpreter"], "interpreter")
    identity = _identity_shape(value["interpreter_identity"], "interpreter", executable=True)
    if identity["path"] != value["interpreter"]:
        _fail("attestation-shape", "interpreter identity does not bind the absolute executable")
    invocation = value["invocation"]
    if type(invocation) is not list or invocation != [value["interpreter"], "-I", LAUNCHER_RELATIVE, "--launch-record", "<launch-record>"]:
        _fail("attestation-shape", "invocation is not the canonical absolute isolated launcher argv")
    if value["module_loading"] != MODULE_LOADING or value["entrypoint"] != ENTRYPOINT:
        _fail("attestation-shape", "module-loading/entrypoint contract is wrong")
    roots = value["runtime_roots"]
    if not isinstance(roots, list) or any(type(item) is not str or not Path(item).is_absolute() for item in roots):
        _fail("attestation-shape", "runtime roots are malformed")
    if [item.encode("utf-8") for item in roots] != sorted(item.encode("utf-8") for item in roots) or len(roots) != len(set(roots)):
        _fail("attestation-shape", "runtime roots are not canonical")
    files = _canonical_identity_list(value["files"], "runtime files")
    modules = value["imported_modules"]
    if not isinstance(modules, list) or len(modules) > MAX_MODULES:
        _fail("attestation-shape", "imported module closure is malformed or oversized")
    normalized_modules: list[dict[str, Any]] = []
    for index, module in enumerate(modules):
        if not isinstance(module, Mapping) or set(module) not in ({"name", "kind", "origin"}, {"name", "kind", "origin", "cached"}) or type(module["name"]) is not str or not module["name"] or type(module["kind"]) is not str or module["kind"] not in {"built-in", "runtime", "source", "extension"}:
            _fail("attestation-shape", f"imported module identity {index} is malformed")
        origin = None if module["origin"] is None else _identity_shape(module["origin"], f"imported_modules[{index}].origin")
        cached = None if module.get("cached") is None else _identity_shape(module["cached"], f"imported_modules[{index}].cached")
        normalized_modules.append({"name": module["name"], "kind": module["kind"], "origin": origin, "cached": cached})
    names = [item["name"] for item in normalized_modules]
    if [item.encode("utf-8") for item in names] != sorted(item.encode("utf-8") for item in names) or len(names) != len(set(names)):
        _fail("attestation-shape", "imported modules are not canonically ordered or contain duplicates")
    loaders = _canonical_identity_list(value["loader_dependencies"], "loader dependencies")
    sys_path = value["sys_path"]
    if not isinstance(sys_path, list) or len(sys_path) > MAX_FILES or any(type(item) is not str or not Path(item).is_absolute() for item in sys_path):
        _fail("attestation-shape", "module/loader/sys.path closure is malformed")
    if [item.encode("utf-8") for item in sys_path] != sorted(item.encode("utf-8") for item in sys_path) or len(sys_path) != len(set(sys_path)):
        _fail("attestation-shape", "sys.path is not canonically ordered or contains duplicates")
    if not isinstance(value["environment_policy"], Mapping) or value["environment_policy"].get("mode") != "sanitized-env-i" or value["environment_policy"].get("ambient") != "excluded":
        _fail("attestation-shape", "environment policy is not the isolated policy")
    expected_canon = {"encoding": "UTF-8", "json": "RFC 8259-compatible strict JSON", "sort_keys": True, "separators": [",", ":"], "ensure_ascii": True, "trailing_newline": True, "self_hash_domain": HASH_DOMAIN.decode("ascii").rstrip("\0"), "self_hash_excludes": ["attestation_sha256"]}
    if value["canonicalization"] != expected_canon or value["attestation_sha256"] != _record_hash({key: value[key] for key in value if key != "attestation_sha256"}):
        _fail("attestation-self-hash", "runtime attestation self hash does not match")
    aggregate = 0
    records = [identity, *files, *loaders]
    record_count = 1 + len(files) + len(loaders) + len(normalized_modules)
    for module in normalized_modules:
        for item in (module["origin"], module["cached"]):
            if item is not None:
                records.append(item)
                record_count += 1
        aggregate += len(module["name"].encode("utf-8")) + len(module["kind"].encode("utf-8"))
    for item in records:
        aggregate += item["bytes"] + len(item["path"].encode("utf-8"))
    aggregate += sum(len(item.encode("utf-8")) for item in roots + sys_path)
    if record_count > MAX_FILES or aggregate > MAX_TOTAL_BYTES:
        _fail("runtime-bound", "runtime closure aggregate exceeds the bound")
    return dict(value)


def validate_attestation(raw_or_value: bytes | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(raw_or_value, bytes):
        if not raw_or_value.endswith(b"\n") or len(raw_or_value) > 2 * 1024 * 1024:
            _fail("attestation-read", "runtime attestation bytes are oversized or not LF terminated")
        try:
            value = json.loads(raw_or_value.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise RuntimeProbeError("attestation-read", "runtime attestation is not strict JSON") from error
        if canonical(value) != raw_or_value:
            _fail("attestation-canonical", "runtime attestation bytes are not canonical")
    elif isinstance(raw_or_value, Mapping):
        value = dict(raw_or_value)
    else:
        _fail("attestation-shape", "runtime attestation must be bytes or an object")
    return _record_shape(value)


def _canonical_sys_path() -> list[str]:
    paths = [Path(item).absolute().as_posix() for item in sys.path if item]
    if len(paths) != len(set(paths)):
        _fail("sys-path", "current sys.path contains duplicate entries")
    return sorted(paths, key=lambda item: item.encode("utf-8"))


def validate_current_attestation(raw_or_value: bytes | Mapping[str, Any], *, expected_selector: str | None = None, check_files: bool = True, require_current_runtime: bool = False) -> dict[str, Any]:
    """Validate a record and optionally its current prepared runtime closure."""
    value = validate_attestation(raw_or_value)
    if expected_selector is not None and value["selector"] != expected_selector:
        _fail("selector", "runtime attestation selector differs from the requested selector")
    if not check_files and not require_current_runtime:
        return value
    for item in [value["interpreter_identity"], *value["files"], *value["loader_dependencies"], *(origin for module in value["imported_modules"] for origin in (module["origin"], module.get("cached")) if origin is not None)]:
        observed = _identity(Path(item["path"]), executable=item is value["interpreter_identity"])
        if any(observed.get(key) != item.get(key) for key in item):
            _fail("file-drift", f"runtime closure identity differs for {item['path']}")
    if require_current_runtime:
        executable = Path(sys.executable).absolute().as_posix()
        if executable != value["interpreter"] or sys.implementation.name != "cpython" or tuple(sys.version_info[:3]) != (3, 13, 15):
            _fail("runtime", "current interpreter does not match the attested CPython 3.13.15 runtime")
        actual_sys_path = _canonical_sys_path()
        if actual_sys_path != value["sys_path"]:
            _fail("sys-path", "current isolated sys.path differs from the attested path")
        policy = _environment_policy()
        if policy != value["environment_policy"]:
            _fail("environment", "current relevant environment policy differs from the attested policy")
        modules, loaders = _runtime_state()
        if modules != value["imported_modules"]:
            _fail("module-closure", "current prepared imported-module closure differs from the attestation")
        if loaders != value["loader_dependencies"]:
            _fail("loader-closure", "current /proc/self/maps loader closure differs from the attestation")
    return value


def attestation_identity(raw: bytes, *, path: str) -> dict[str, Any]:
    value = validate_attestation(raw)
    _path(path, "attestation path", absolute=False)
    return {"path": path, "bytes": len(raw), "sha256": _sha(raw), "attestation_sha256": value["attestation_sha256"]}


def probe_runtime(selector: str, *, output_path: Path | None = None) -> tuple[dict[str, Any], bytes]:
    """Capture the current interpreter; callers must run this under 3.13.15."""
    if selector not in SELECTORS:
        _fail("selector", "runtime selector is not canonical")
    if sys.implementation.name != "cpython" or tuple(sys.version_info[:3]) != (3, 13, 15):
        _fail("runtime", "probe must run under CPython 3.13.15")
    executable = Path(sys.executable).absolute()
    interpreter_identity = _identity(executable, executable=True)
    roots = []
    for key in ("stdlib", "platstdlib"):
        candidate = sysconfig.get_path(key)
        if candidate and Path(candidate).is_absolute():
            roots.append(Path(candidate))
    roots = sorted(set(roots), key=lambda item: item.as_posix().encode("utf-8"))
    prefixes = sorted({Path(sys.prefix).resolve(), Path(sys.base_prefix).resolve()}, key=lambda item: item.as_posix().encode("utf-8"))
    modules, loader = _runtime_state()
    files = _runtime_files(prefixes, roots)
    for module in modules:
        for origin in (module["origin"], module["cached"]):
            if origin is not None and origin not in files:
                files.append(origin)
    if interpreter_identity not in files:
        files.append(interpreter_identity)
    for identity in loader:
        if identity not in files:
            files.append(identity)
    files.sort(key=lambda item: item["path"].encode("utf-8"))
    unsigned = {
        "schema": SCHEMA, "selector": selector, "implementation": IMPLEMENTATION, "version": VERSION,
        "interpreter": executable.as_posix(), "interpreter_identity": interpreter_identity,
        "invocation": [executable.as_posix(), "-I", LAUNCHER_RELATIVE, "--launch-record", "<launch-record>"],
        "module_loading": MODULE_LOADING, "entrypoint": ENTRYPOINT,
        "runtime_roots": [item.as_posix() for item in roots], "files": files, "imported_modules": modules,
        "loader_dependencies": loader, "sys_path": _canonical_sys_path(),
        "environment_policy": _environment_policy(),
        "canonicalization": {"encoding": "UTF-8", "json": "RFC 8259-compatible strict JSON", "sort_keys": True, "separators": [",", ":"], "ensure_ascii": True, "trailing_newline": True, "self_hash_domain": HASH_DOMAIN.decode("ascii").rstrip("\0"), "self_hash_excludes": ["attestation_sha256"]},
    }
    unsigned["attestation_sha256"] = _record_hash(unsigned)
    raw = canonical(unsigned)
    validate_attestation(raw)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(raw)
    return unsigned, raw


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="capture one bounded Phase 3 CPython runtime attestation")
    parser.add_argument("--selector", required=True, choices=SELECTORS)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        probe_runtime(args.selector, output_path=args.output)
    except RuntimeProbeError as error:
        print(f"PHASE 3 PYTHON RUNTIME PROBE FAILED: {error}", file=sys.stderr)
        return 1
    print(f"PHASE 3 PYTHON RUNTIME ATTESTATION CREATED: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "SCHEMA", "CONTRACT_SCHEMA", "ATTESTATION_PATHS", "FROZEN_PHASE3_SCRIPT_FILES",
    "FROZEN_PHASE3_STDLIB_MODULES", "FROZEN_PHASE3_STDLIB_TOP_LEVEL", "RuntimeProbeError",
    "canonical", "prepare_runtime_import_closure", "validate_attestation",
    "validate_current_attestation", "attestation_identity", "probe_runtime",
]

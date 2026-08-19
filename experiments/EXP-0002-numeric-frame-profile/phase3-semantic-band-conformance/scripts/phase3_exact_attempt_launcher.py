#!/usr/bin/env python3
"""Fail-closed CPython launcher for one Phase 3 exact attempt.

The launch record is the only CLI input.  It is a small canonical JSON object
whose paths identify the already-authenticated package records; the launcher
reads those records as exact bytes, authenticates the v4 runtime contract, and
only then calls the production ``run_exact_attempt`` entrypoint.  No retry,
candidate-path, environment, or alternate module-loading choice is accepted.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys
import types
from types import MappingProxyType
from typing import Any, Mapping, Sequence


LAUNCH_RECORD_SCHEMA = "ck.exp-0002.phase3.exact-attempt-launch-1"
FREEZE_SCHEMA = "ck.exp-0002.phase3.freeze-manifest-4"
PYTHON_RUNTIME_CONTRACT_SCHEMA = "ck.exp-0002.phase3.python-runtime-contract-1"
PYTHON_VERSION = "3.13.15"
PYTHON_INVOCATION = (
    "python3.13", "-I", "scripts/phase3_exact_attempt_launcher.py",
    "--launch-record", "<launch-record>",
)
PYTHON_MODULE_LOADING = "explicit-sibling-file-loading-under-isolated-mode"
PYTHON_ENTRYPOINT = "phase3_exact_attempt_launcher.main->phase3_exact_attempt.run_exact_attempt"
SELECTORS = MappingProxyType({"wsl2-x86_64": frozenset({0, 1}), "ubuntu-24.04-x86_64": frozenset({2})})
LAUNCH_KEYS = frozenset({
    "schema", "package_root", "attempt_id", "platform_selector", "ordinal",
    "freeze_manifest_path", "admission_record_path", "authorization_record_path",
    "custody_record_path", "review_root", "output_root", "work_root",
})
MAX_RECORD_BYTES = 64 * 1024
MAX_FREEZE_BYTES = 2 * 1024 * 1024
MAX_PATH_BYTES = 4096
MAX_JSON_DEPTH = 24
MAX_TOOL_IDENTITIES = 32
SCRIPT_RELATIVE_PATH = "scripts/phase3_exact_attempt_launcher.py"
_SIBLING_DIR = Path(__file__).resolve().parent
_LOAD_ROOT = _SIBLING_DIR.parent
_RETAINED_SIBLING_BYTES: dict[str, bytes] = {}


class LauncherError(ValueError):
    """Bounded, stable launcher failure."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = str(code)
        self.detail = str(detail).replace("\x00", "?").replace("\r", " ").replace("\n", " ")[:512]
        super().__init__(f"{self.code}: {self.detail}" if self.detail else self.code)


def _fail(code: str, detail: str = "") -> None:
    raise LauncherError(code, detail)


def _canonical(value: Any) -> bytes:
    try:
        return (json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise LauncherError("canonical-json", "value cannot be represented as canonical JSON") from error


def _depth(value: Any, level: int = 0) -> None:
    if level > MAX_JSON_DEPTH:
        _fail("record-depth", "JSON exceeds the bounded nesting depth")
    if isinstance(value, dict):
        for key, child in value.items():
            if type(key) is not str:
                _fail("record-key", "JSON object key is not a string")
            _depth(child, level + 1)
    elif isinstance(value, list):
        for child in value:
            _depth(child, level + 1)


def _parse_record(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > MAX_RECORD_BYTES or not raw.endswith(b"\n"):
        _fail("record-size", f"{label} is absent, oversized, or missing its trailing newline")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                _fail("duplicate-json-key", f"{label} contains duplicate {key}")
            result[key] = value
        return result

    def constant(token: str) -> None:
        _fail("nonfinite-json", f"{label} contains {token}")

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)
    except LauncherError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as error:
        raise LauncherError("malformed-json", f"{label} is not strict JSON") from error
    _depth(value)
    if type(value) is not dict:
        _fail("record-shape", f"{label} must be a JSON object")
    if _canonical(value) != raw:
        _fail("noncanonical", f"{label} is not canonical JSON")
    return value


def _parse_freeze_raw(raw: bytes) -> dict[str, Any]:
    """Parse the freeze before importing its validator.

    This bootstrap parser is intentionally only the strict JSON/canonical-byte
    gate.  The canonical freeze module is loaded only after its own frozen
    identity has been authenticated from this parsed value.
    """
    if type(raw) is not bytes or not raw or len(raw) > MAX_FREEZE_BYTES or not raw.endswith(b"\n"):
        _fail("freeze-size", "freeze manifest is absent, oversized, or missing its trailing newline")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                _fail("duplicate-json-key", f"freeze manifest contains duplicate {key}")
            result[key] = value
        return result

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=lambda token: _fail("nonfinite-json", token))
    except LauncherError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as error:
        raise LauncherError("malformed-json", "freeze manifest is not strict JSON") from error
    _depth(value)
    if type(value) is not dict or _canonical(value) != raw:
        _fail("noncanonical", "freeze manifest is not canonical JSON")
    return value


def _path_text(value: Any, label: str, *, relative: bool | None = None, allow_dot: bool = False) -> str:
    if type(value) is not str or not value or "\x00" in value or "\\" in value:
        _fail("path", f"{label} is not a safe path")
    try:
        if len(value.encode("utf-8")) > MAX_PATH_BYTES:
            _fail("path-size", f"{label} exceeds the path byte bound")
    except UnicodeEncodeError as error:
        raise LauncherError("path", f"{label} is not UTF-8") from error
    path = Path(value)
    if relative is True and path.is_absolute():
        _fail("path", f"{label} must be relative")
    if relative is False and not path.is_absolute():
        _fail("path", f"{label} must be absolute")
    for part in path.parts:
        if part in {"..", ""} or (part == "." and not allow_dot):
            _fail("path", f"{label} contains an unsafe component")
    return value


def _reject_symlink_components(path: Path) -> None:
    """Retain a cheap early diagnostic; descriptor walks remain authoritative."""
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        try:
            info = current.lstat()
        except FileNotFoundError:
            break
        except OSError as error:
            raise LauncherError("path", f"cannot inspect {path}") from error
        if stat.S_ISLNK(info.st_mode):
            _fail("symlink", f"{path} contains a symlink component")


def _resolve_path(value: str, base: Path, label: str, *, allow_absolute: bool, allow_dot: bool = False) -> Path:
    _path_text(value, label, relative=None if allow_absolute else True, allow_dot=allow_dot)
    path = Path(value) if Path(value).is_absolute() else base / value
    path = Path(os.path.normpath(str(path)))
    if not path.is_absolute() or len(os.fsencode(str(path))) > MAX_PATH_BYTES:
        _fail("path", f"{label} is not a bounded absolute path")
    _reject_symlink_components(path)
    return path


def _open_anchored_parent(path: Path, label: str) -> tuple[int, str]:
    """Walk from the filesystem root with O_NOFOLLOW for every component."""
    absolute = path.absolute()
    if not absolute.is_absolute() or len(absolute.parts) < 2:
        _fail("path", f"{label} is not an absolute file path")
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    parent = -1
    try:
        parent = os.open(os.sep, flags)
        for component in absolute.parts[1:-1]:
            child = os.open(component, flags, dir_fd=parent)
            os.close(parent)
            parent = child
        return parent, absolute.parts[-1]
    except LauncherError:
        if parent >= 0:
            os.close(parent)
        raise
    except OSError as error:
        if parent >= 0:
            os.close(parent)
        raise LauncherError("record-read", f"cannot open anchored parent for {label}") from error


def _read_exact(path: Path, label: str, *, limit: int = MAX_RECORD_BYTES, expected_mode: int | None = None) -> bytes:
    """Read an exact file through anchored descriptors and stable identities."""
    parent, name = _open_anchored_parent(path, label)
    fd = -1
    try:
        before_path = os.stat(name, dir_fd=parent, follow_symlinks=False)
        if stat.S_ISLNK(before_path.st_mode) or not stat.S_ISREG(before_path.st_mode) or before_path.st_nlink != 1:
            _fail("record-size", f"{label} is not a bounded single-link regular file")
        if expected_mode is not None and stat.S_IMODE(before_path.st_mode) != expected_mode:
            _fail("record-mode", f"{label} does not have the frozen mode")
        if before_path.st_size <= 0 or before_path.st_size > limit:
            _fail("record-size", f"{label} is outside its bounded size")
        fd = os.open(name, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0), dir_fd=parent)
        before = os.fstat(fd)
        expected = (before_path.st_dev, before_path.st_ino, before_path.st_mode, before_path.st_nlink, before_path.st_size, before_path.st_mtime_ns, before_path.st_ctime_ns)
        opened = (before.st_dev, before.st_ino, before.st_mode, before.st_nlink, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
        if opened != expected:
            _fail("record-race", f"{label} changed before being read")
        chunks: list[bytes] = []
        total = 0
        while True:
            part = os.read(fd, min(1024 * 1024, limit + 1 - total))
            if not part:
                break
            total += len(part)
            if total > limit:
                _fail("record-size", f"{label} grew beyond its bound")
            chunks.append(part)
        raw = b"".join(chunks)
        after = os.fstat(fd)
        after_path = os.stat(name, dir_fd=parent, follow_symlinks=False)
        after_identity = (after.st_dev, after.st_ino, after.st_mode, after.st_nlink, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
        path_identity = (after_path.st_dev, after_path.st_ino, after_path.st_mode, after_path.st_nlink, after_path.st_size, after_path.st_mtime_ns, after_path.st_ctime_ns)
        if after_identity != expected or path_identity != after_identity or len(raw) != before_path.st_size:
            _fail("record-race", f"{label} changed while being read")
        return raw
    except LauncherError:
        raise
    except OSError as error:
        raise LauncherError("record-read", f"cannot read {label}") from error
    finally:
        if fd >= 0:
            os.close(fd)
        os.close(parent)


def _validate_launch_record(value: Mapping[str, Any]) -> dict[str, Any]:
    if set(value) != LAUNCH_KEYS:
        _fail("launch-record-shape", "launch record has missing or unexpected fields")
    if value["schema"] != LAUNCH_RECORD_SCHEMA:
        _fail("launch-record-schema", "launch record schema is unsupported")
    if type(value["attempt_id"]) is not str or re.fullmatch(r"attempt-[A-Za-z0-9][A-Za-z0-9._-]{2,127}", value["attempt_id"]) is None:
        _fail("attempt-id", "launch record attempt_id is malformed")
    selector = value["platform_selector"]
    ordinal = value["ordinal"]
    if selector not in SELECTORS or type(ordinal) is not int or ordinal not in SELECTORS[selector]:
        _fail("platform", "launch record selector/ordinal is not preregistered")
    _path_text(value["package_root"], "package_root", relative=None, allow_dot=True)
    for field in ("freeze_manifest_path", "admission_record_path", "authorization_record_path", "custody_record_path"):
        _path_text(value[field], field, relative=True)
    for field in ("review_root", "output_root", "work_root"):
        _path_text(value[field], field, relative=None, allow_dot=True)
    return dict(value)


def _load_sibling_module(filename: str, module_name: str, *, raw: bytes | None = None, root: Path | None = None) -> Any:
    """Compile/execute retained sibling bytes with transactional registration."""
    if not filename or "/" in filename or "\\" in filename or Path(filename).name != filename:
        _fail("module-loading", "sibling module filename is not closed")
    path = (root or _LOAD_ROOT) / "scripts" / filename
    if raw is None:
        raw = _RETAINED_SIBLING_BYTES.get(f"scripts/{filename}")
    if raw is None:
        raw = _read_exact(path, f"sibling {filename}", limit=16 * 1024 * 1024, expected_mode=0o644)
    try:
        code = compile(raw, str(path), "exec", dont_inherit=True, optimize=0)
    except (SyntaxError, TypeError, ValueError) as error:
        raise LauncherError("module-loading", f"sibling {filename} did not compile") from error
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None:
        _fail("module-loading", f"cannot create module spec for sibling {filename}")
    module = types.ModuleType(module_name)
    module.__file__ = str(path)
    module.__loader__ = None
    module.__package__ = ""
    module.__spec__ = spec
    previous = sys.modules.get(module_name)
    sys.modules[module_name] = module
    try:
        exec(code, module.__dict__)
    except Exception as error:
        if previous is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = previous
        raise LauncherError("module-loading", f"sibling {filename} failed to load") from error
    return module


def _raw_tool_identities(value: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return all v4 tool identities, retaining the closure tool separately."""
    result: list[dict[str, Any]] = []
    for field in ("runtime_tool_identities", "exact_runtime_tool_identities", "provenance_tool_identities", "experiment_closure_tool_identities"):
        collection = value.get(field)
        if not isinstance(collection, list) or not collection:
            _fail("tool-closure", f"freeze {field} is absent")
        for identity in collection:
            if not isinstance(identity, Mapping) or set(identity) != {"path", "mode", "bytes", "sha256"} or identity.get("mode") != 0o644:
                _fail("tool-closure", f"freeze {field} contains a malformed identity")
            path = identity.get("path")
            if type(path) is not str or not path.startswith("scripts/") or "\\" in path or any(part in {"", ".", ".."} for part in path.split("/")):
                _fail("tool-closure", f"freeze {field} contains an unsafe path")
            if type(identity.get("bytes")) is not int or identity["bytes"] <= 0 or identity["bytes"] > 16 * 1024 * 1024:
                _fail("tool-closure", f"freeze {field} contains an invalid size")
            digest = identity.get("sha256")
            if type(digest) is not str or len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
                _fail("tool-closure", f"freeze {field} contains an invalid digest")
            result.append({"path": path, "mode": 0o644, "bytes": identity["bytes"], "sha256": digest})
    if len(result) != 21:
        _fail("tool-closure", "v4 freeze must bind 20 exact-runtime tools plus one closure tool")
    if len({item["path"] for item in result}) != len(result):
        _fail("tool-closure", "freeze tool identities contain duplicate paths")
    return result


def _validate_sibling_identities(raw: bytes, package_root: Path) -> dict[str, bytes]:
    parsed = _parse_freeze_raw(raw)
    if parsed.get("schema") != FREEZE_SCHEMA:
        _fail("freeze-version", "exact launcher requires the v4 freeze manifest")
    identities = _raw_tool_identities(parsed)
    retained: dict[str, bytes] = {}
    for identity in identities:
        path = identity["path"]
        file_bytes = _read_exact(package_root / path, path, limit=16 * 1024 * 1024, expected_mode=0o644)
        if len(file_bytes) != identity["bytes"] or hashlib.sha256(file_bytes).hexdigest() != identity["sha256"]:
            _fail("tool-identity", f"frozen sibling identity differs for {path}")
        retained[path] = file_bytes
    launcher = retained.get(SCRIPT_RELATIVE_PATH)
    if launcher is None:
        _fail("tool-identity", "v4 freeze does not bind the exact launcher source")
    try:
        running = _read_exact(Path(__file__).resolve(), "launcher self", limit=16 * 1024 * 1024, expected_mode=0o644)
    except LauncherError:
        raise
    if running != launcher:
        _fail("tool-identity", "running launcher bytes differ from frozen launcher identity")
    return retained


def _validate_freeze(raw: bytes, *, package_root: Path | None = None) -> dict[str, Any]:
    """Authenticate sibling identities before loading the canonical validator."""
    global _RETAINED_SIBLING_BYTES, _LOAD_ROOT
    root = package_root or _LOAD_ROOT
    retained = _validate_sibling_identities(raw, root)
    _RETAINED_SIBLING_BYTES = retained
    _LOAD_ROOT = root
    freeze_module = _load_sibling_module(
        "phase3_freeze_manifest.py", "phase3_freeze_manifest",
        raw=retained["scripts/phase3_freeze_manifest.py"], root=root,
    )
    try:
        value = freeze_module.validate_manifest(raw)
    except Exception as error:
        raise LauncherError("freeze", "canonical freeze validator rejected the supplied bytes") from error
    if value.get("schema") != FREEZE_SCHEMA:
        _fail("freeze-version", "exact launcher requires the v4 freeze manifest")
    return value


def _normalized_orig_argv(argv: Sequence[str], orig_argv: Any) -> list[str]:
    if type(orig_argv) is not list or len(orig_argv) != 5 or any(type(item) is not str or not item for item in orig_argv):
        _fail("invocation", "sys.orig_argv is not the exact five-argument invocation")
    if len(argv) != 2 or argv[0] != "--launch-record" or not isinstance(argv[1], str):
        _fail("invocation", "launcher argv is not the exact launch-record form")
    interpreter = Path(orig_argv[0]).name
    if interpreter != "python3.13":
        _fail("invocation", "sys.orig_argv interpreter is not python3.13")
    if orig_argv[1] != "-I" or orig_argv[3] != "--launch-record":
        _fail("invocation", "sys.orig_argv is missing the isolated launcher flags")
    script = orig_argv[2].replace("\\", "/")
    if script.startswith("/") or os.path.normpath(script) != SCRIPT_RELATIVE_PATH:
        _fail("invocation", "sys.orig_argv entrypoint path is not canonical")
    _path_text(orig_argv[4], "sys.orig_argv launch record", relative=None)
    if orig_argv[4] != argv[1]:
        _fail("invocation", "sys.orig_argv launch record differs from sys.argv")
    return ["python3.13", "-I", SCRIPT_RELATIVE_PATH, "--launch-record", "<launch-record>"]


def _runtime_preflight(freeze: Mapping[str, Any], selector: str, argv: Sequence[str], orig_argv: Any) -> None:
    contract = freeze.get("exact_python_runtime_contract")
    if not isinstance(contract, Mapping) or set(contract) != {"schema", "platforms"} or contract.get("schema") != PYTHON_RUNTIME_CONTRACT_SCHEMA:
        _fail("runtime-contract", "freeze does not bind the exact Python runtime contract")
    platforms = contract.get("platforms")
    if not isinstance(platforms, Mapping) or set(platforms) != set(SELECTORS):
        _fail("runtime-contract", "freeze runtime contract does not bind both selectors")
    selected = platforms.get(selector)
    expected_keys = {"selector", "implementation", "version", "invocation", "module_loading", "entrypoint"}
    if not isinstance(selected, Mapping) or set(selected) != expected_keys or selected.get("selector") != selector:
        _fail("runtime-contract", "selected runtime contract is not closed")
    if selected.get("implementation") != "CPython" or selected.get("version") != PYTHON_VERSION:
        _fail("runtime-contract", "selected runtime contract is not CPython 3.13.15")
    if selected.get("invocation") != list(PYTHON_INVOCATION) or selected.get("module_loading") != PYTHON_MODULE_LOADING or selected.get("entrypoint") != PYTHON_ENTRYPOINT:
        _fail("runtime-contract", "selected runtime invocation/module-loading contract differs")
    implementation = getattr(sys, "implementation", None)
    if getattr(implementation, "name", None) != "cpython":
        _fail("runtime", "actual interpreter is not CPython")
    version = getattr(sys, "version_info", None)
    if version is None or (getattr(version, "major", None), getattr(version, "minor", None), getattr(version, "micro", None)) != (3, 13, 15):
        _fail("runtime", "actual interpreter is not CPython 3.13.15")
    if type(getattr(getattr(sys, "flags", None), "isolated", None)) is not int or getattr(sys.flags, "isolated") != 1:
        _fail("runtime", "isolated mode (-I) is not active")
    if _normalized_orig_argv(argv, orig_argv) != list(selected["invocation"]):
        _fail("invocation", "normalized sys.orig_argv differs from the authenticated freeze")


def _candidate_identity(freeze: Mapping[str, Any]) -> dict[str, Any]:
    closure = freeze.get("candidate_closure")
    if not isinstance(closure, Mapping):
        _fail("candidate-identity", "freeze candidate closure is absent")
    keys = ("algorithm", "count", "path_set_sha256", "content_sha256", "total_raw_bytes")
    if any(key not in closure for key in keys):
        _fail("candidate-identity", "freeze candidate closure is incomplete")
    return {key: closure[key] for key in keys}


def _tool_identities(freeze: Mapping[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for field in ("runtime_tool_identities", "exact_runtime_tool_identities", "provenance_tool_identities"):
        collection = freeze.get(field)
        if not isinstance(collection, list) or not collection:
            _fail("tool-closure", f"freeze {field} is absent")
        for identity in collection:
            if not isinstance(identity, Mapping) or set(identity) != {"path", "mode", "bytes", "sha256"} or identity.get("mode") != 0o644:
                _fail("tool-closure", f"freeze {field} contains a malformed identity")
            result.append({key: identity[key] for key in ("path", "bytes", "sha256")})
    if len(result) != 20 or len(result) > MAX_TOOL_IDENTITIES:
        _fail("tool-closure", "freeze tool closure exceeds the bound")
    return result


def _build_inputs(record: Mapping[str, Any], launch_path: Path, freeze: Mapping[str, Any], freeze_raw: bytes) -> dict[str, Any]:
    package_root = _resolve_path(record["package_root"], Path.cwd(), "package_root", allow_absolute=True, allow_dot=True)
    if not package_root.is_dir():
        _fail("package-root", "package_root is not a directory")
    if Path.cwd() != package_root:
        _fail("package-root", "launcher must run from the package boundary")
    refs = {
        "admission_record": record["admission_record_path"],
        "authorization_record": record["authorization_record_path"],
        "custody_record": record["custody_record_path"],
    }
    record_bytes: dict[str, bytes] = {"freeze_manifest": freeze_raw}
    for name, relative in refs.items():
        path = _resolve_path(relative, package_root, name, allow_absolute=False)
        record_bytes[name] = _read_exact(path, name)
        _parse_record(record_bytes[name], name)
    review_root = _resolve_path(record["review_root"], package_root, "review_root", allow_absolute=True, allow_dot=True)
    output_root = _resolve_path(record["output_root"], package_root, "output_root", allow_absolute=True, allow_dot=True)
    work_root = _resolve_path(record["work_root"], package_root, "work_root", allow_absolute=True, allow_dot=True)
    if not review_root.is_dir():
        _fail("review-root", "review_root is not a directory")
    return {
        "package_root": package_root,
        "attempt_id": record["attempt_id"],
        "platform_selector": record["platform_selector"],
        "ordinal": record["ordinal"],
        "freeze_manifest": freeze_raw,
        "admission_record": record_bytes["admission_record"],
        "authorization_record": record_bytes["authorization_record"],
        "custody_record": record_bytes["custody_record"],
        "review_root": review_root,
        "candidate_identity": _candidate_identity(freeze),
        "tool_identities": _tool_identities(freeze),
        "output_root": output_root,
        "work_root": work_root,
    }


def _invoke_exact_attempt(**inputs: Any) -> Any:
    """Private final-call seam used only by bounded launcher tests."""
    # Import every dependency by an explicit sibling path.  The order follows
    # the import graph of phase3_exact_attempt and does not modify sys.path.
    for filename in (
        "phase3_common.py", "phase3_oracle.py", "phase3_scorer.py", "phase3_runner.py",
        "phase3_materialized_adapter.py", "phase3_evidence_contract.py", "phase3_exact_fp_observer.py",
        "phase3_exact_transport.py", "phase3_exact_adjudicator.py", "phase3_gate_b_preflight.py",
        "phase3_build_receipt.py", "phase3_freeze_manifest.py",
        "phase3_exact_authority.py", "phase3_exact_custody.py", "phase3_exact_publication.py",
    ):
        name = Path(filename).stem
        retained = _RETAINED_SIBLING_BYTES.get(f"scripts/{filename}")
        _load_sibling_module(filename, name, raw=retained)
    module = _load_sibling_module("phase3_exact_attempt.py", "phase3_exact_attempt")
    return module.run_exact_attempt(**inputs)


HELP = "usage: python3.13 -I scripts/phase3_exact_attempt_launcher.py --launch-record <launch-record>\n"


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args == ["--help"]:
        sys.stdout.write(HELP)
        return 0
    if len(args) != 2 or args[0] != "--launch-record":
        _fail("usage", "only --launch-record <path> is accepted")
    launch_path = _resolve_path(args[1], Path.cwd(), "launch record", allow_absolute=True)
    launch_raw = _read_exact(launch_path, "launch record")
    record = _validate_launch_record(_parse_record(launch_raw, "launch record"))
    package_root = _resolve_path(record["package_root"], Path.cwd(), "package_root", allow_absolute=True, allow_dot=True)
    freeze_path = _resolve_path(record["freeze_manifest_path"], package_root, "freeze_manifest_path", allow_absolute=False)
    freeze_raw = _read_exact(freeze_path, "freeze manifest")
    freeze = _validate_freeze(freeze_raw, package_root=package_root)
    _runtime_preflight(freeze, record["platform_selector"], args, list(getattr(sys, "orig_argv", ())))
    inputs = _build_inputs(record, launch_path, freeze, freeze_raw)
    _invoke_exact_attempt(**inputs)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except LauncherError as error:
        sys.stderr.write(f"phase3 exact launcher: {error.code}\n")
        raise SystemExit(2)
    except Exception:
        sys.stderr.write("phase3 exact launcher: launcher\n")
        raise SystemExit(2)


__all__ = ["LAUNCH_RECORD_SCHEMA", "LauncherError", "main"]

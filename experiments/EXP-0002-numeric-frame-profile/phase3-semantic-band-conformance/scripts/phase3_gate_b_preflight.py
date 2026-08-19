"""Read-only Gate B readiness preflight for the Phase 3 package.

The preflight consumes the existing materialized package and caller-supplied
content identities.  Its freeze checker reads the two committed source
snapshots, but it never runs Cargo, a candidate, a shell, or an environment
probe, and it never creates a freeze manifest or changes package state.  A
successful call therefore reports readiness *blocked* by the remaining Gate B
bindings rather than authorizing execution.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import stat
import sys
import types
from pathlib import Path
from typing import Any, Mapping

from phase3_materialized_adapter import load_materialized_cases


SCHEMA = "ck.exp-0002.phase3.gate-b-preflight-3"
EVIDENCE_SCHEMA = "ck.exp-0002.phase3.evidence-proposed-1"
EXPECTED_ALGORITHM = "ck.phase3-candidate-source-build-closure.v1"
EXPECTED_CANDIDATE_COUNT = 47
EXPECTED_PATH_SHA256 = "10605701d02f117ff7ef2756004fbf53a475eb92fbc0616e139f919d7a8480dc"
EXPECTED_CONTENT_SHA256 = "21825e78c3286cf73d135f44be99eaea5214ce36b5fed6271dce096d364468e2"
EXPECTED_CANDIDATE_BYTES = 1_494_337
EXPECTED_PHASE = "exp-0002-phase3-semantic-band-conformance-001"
EXPECTED_PROFILE = "ck.provisional-r3-authored-conflict.semantic-band-1"
REPOSITORY = Path(__file__).resolve().parents[4]
GIT_EXECUTABLE = "/usr/bin/git"
FREEZE_MANIFEST_PATH = "manifests/freeze-manifest.json"
FREEZE_RECEIPT_DIR = "manifests/build-receipts"
FREEZE_RECEIPT_NAMES = frozenset({"wsl.json", "native.json"})
FREEZE_SCRIPT_PATH = "scripts/phase3_freeze_manifest.py"
CORE_TOOL_PATHS = (
    "scripts/phase3_common.py",
    "scripts/phase3_oracle.py",
    "scripts/phase3_scorer.py",
    "scripts/phase3_runner.py",
    "scripts/phase3_receipt.py",
    "scripts/phase3_materialized_adapter.py",
    "scripts/phase3_evidence_contract.py",
    "scripts/phase3_gate_b_preflight.py",
)
EXACT_TOOL_PATHS = (
    "scripts/phase3_exact_adjudicator.py",
    "scripts/phase3_exact_authority.py",
    "scripts/phase3_exact_custody.py",
    "scripts/phase3_exact_fp_observer.py",
    "scripts/phase3_exact_publication.py",
    "scripts/phase3_exact_transport.py",
    "scripts/phase3_exact_attempt.py",
)
V5_EXACT_TOOL_PATHS = (*EXACT_TOOL_PATHS, "scripts/phase3_exact_attempt_launcher.py")
PROVENANCE_TOOL_PATHS = (
    "scripts/generate_phase3.py",
    "scripts/check_candidate_prebinding.py",
    "scripts/phase3_build_receipt.py",
    "scripts/phase3_freeze_manifest.py",
)
EXPERIMENT_CLOSURE_TOOL_PATHS = ("scripts/phase3_experiment_closure.py",)
TOOL_PATHS = (*CORE_TOOL_PATHS, *EXACT_TOOL_PATHS, *PROVENANCE_TOOL_PATHS)
V4_TOOL_PATHS = (*CORE_TOOL_PATHS, *V5_EXACT_TOOL_PATHS, *PROVENANCE_TOOL_PATHS)
V5_TOOL_PATHS = (*CORE_TOOL_PATHS, *V5_EXACT_TOOL_PATHS, *PROVENANCE_TOOL_PATHS, "scripts/phase3_python_runtime_probe.py")
MAX_IDENTITY_BYTES = 8 * 1024 * 1024
MAX_STRING_BYTES = 4096
SHA256_RE = set("0123456789abcdef")


class GateBPreflightError(ValueError):
    """Stable read-only preflight error."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = str(code)
        self.detail = str(detail).replace("\x00", "?").replace("\n", " ").replace("\r", "")[:256]
        super().__init__(f"{self.code}: {self.detail}" if self.detail else self.code)


def _fail(code: str, detail: str) -> None:
    raise GateBPreflightError(code, detail)


def _plain(value: Any, label: str, depth: int = 0) -> None:
    if depth > 16:
        _fail("nesting-limit", f"{label} is too deeply nested")
    if callable(value) or isinstance(value, (Path, os.PathLike)):
        _fail("forbidden-value", f"{label} is callable or path-like")
    if type(value) is float:
        import math
        if not math.isfinite(value):
            _fail("nonfinite", f"{label} is non-finite")
        return
    if value is None or type(value) in (bool, int):
        return
    if type(value) is str:
        if len(value.encode("utf-8")) > MAX_STRING_BYTES:
            _fail("string-limit", f"{label} is oversized")
        return
    if type(value) is list:
        if len(value) > 256:
            _fail("array-limit", f"{label} is oversized")
        for index, item in enumerate(value):
            _plain(item, f"{label}[{index}]", depth + 1)
        return
    if type(value) is dict:
        if len(value) > 128:
            _fail("object-limit", f"{label} is oversized")
        forbidden = {
            "execute", "execution", "execution_permitted", "run", "command", "cmd", "shell",
            "argv", "cwd", "env", "environment", "ack", "acknowledgement", "acknowledgment",
            "candidate_path", "candidate_binary", "candidate_executable", "executable",
            "subprocess", "process", "spawn", "workflow_command", "path_to_run",
        }
        for key, item in value.items():
            if type(key) is not str:
                _fail("forbidden-value", f"{label} has a non-string key")
            lowered = key.lower()
            if lowered in forbidden or any(token in lowered for token in ("execution", "command", "shell", "acknowledg")):
                _fail("forbidden-field", f"{label}.{key} is forbidden in preflight input")
            _plain(item, f"{label}.{key}", depth + 1)
        return
    _fail("forbidden-value", f"{label} has unsupported type {type(value).__name__}")


def _string(value: Any, label: str, *, nonempty: bool = True) -> str:
    if type(value) is not str or (nonempty and not value):
        _fail("identity-shape", f"{label} must be a string")
    try:
        if len(value.encode("utf-8")) > MAX_STRING_BYTES:
            _fail("string-limit", f"{label} is oversized")
    except UnicodeEncodeError as error:
        raise GateBPreflightError("invalid-utf8", f"{label} is not UTF-8") from error
    return value


def _sha(value: Any, label: str) -> str:
    value = _string(value, label)
    if len(value) != 64 or any(char not in SHA256_RE for char in value):
        _fail("identity-shape", f"{label} is not a lowercase SHA-256")
    return value


def _bounded_int(value: Any, label: str, maximum: int = 8 * 1024 * 1024) -> int:
    if type(value) is not int or not 0 <= value <= maximum:
        _fail("identity-shape", f"{label} is not bounded")
    return value


def _candidate_identity(value: Any) -> dict[str, Any]:
    _plain(value, "candidate_identity")
    if type(value) is not dict:
        _fail("identity-shape", "candidate identity must be an object")
    allowed = {
        "algorithm", "count", "path_set_sha256", "content_sha256", "total_raw_bytes",
        "total_bytes", "bytes", "path_set", "content", "base_commit", "current_disk",
    }
    if not set(value) <= allowed:
        _fail("identity-shape", "candidate identity has unexpected members")
    if value.get("algorithm") != EXPECTED_ALGORITHM:
        _fail("candidate-identity", "candidate closure algorithm differs")
    count = value.get("count")
    path_sha = value.get("path_set_sha256")
    content_sha = value.get("content_sha256")
    total = value.get("total_raw_bytes")
    aliases = [value[key] for key in ("total_bytes", "bytes") if key in value]
    if total is None and aliases:
        total = aliases[0]
    if aliases and any(alias != total for alias in aliases):
        _fail("candidate-identity", "candidate byte-count identities disagree")
    path_set = value.get("path_set")
    content = value.get("content")
    if type(path_set) is dict:
        if set(path_set) != {"count", "sha256"}:
            _fail("identity-shape", "candidate path_set is not closed")
        count = path_set["count"] if count is None else count
        path_sha = path_set["sha256"] if path_sha is None else path_sha
        if count != path_set["count"] or path_sha != path_set["sha256"]:
            _fail("candidate-identity", "candidate path-set identities disagree")
    if type(content) is dict:
        if set(content) != {"sha256", "total_raw_bytes"}:
            _fail("identity-shape", "candidate content is not closed")
        content_sha = content["sha256"] if content_sha is None else content_sha
        total = content["total_raw_bytes"] if total is None else total
        if content_sha != content["sha256"] or total != content["total_raw_bytes"]:
            _fail("candidate-identity", "candidate content identities disagree")
    if count != EXPECTED_CANDIDATE_COUNT:
        _fail("candidate-identity", "candidate closure count differs")
    _sha(path_sha, "candidate path-set SHA")
    _sha(content_sha, "candidate content SHA")
    _bounded_int(total, "candidate raw bytes", MAX_IDENTITY_BYTES)
    if path_sha != EXPECTED_PATH_SHA256 or content_sha != EXPECTED_CONTENT_SHA256 or total != EXPECTED_CANDIDATE_BYTES:
        _fail("candidate-identity", "candidate closure identity differs")
    return {
        "algorithm": EXPECTED_ALGORITHM,
        "count": EXPECTED_CANDIDATE_COUNT,
        "path_set_sha256": path_sha,
        "content_sha256": content_sha,
        "total_raw_bytes": total,
    }


def _manifest_candidate_identity(manifest: Mapping[str, Any]) -> dict[str, Any]:
    closure = manifest.get("candidate_closure")
    if not isinstance(closure, Mapping):
        _fail("freeze-manifest", "freeze manifest candidate closure is unavailable")
    try:
        return {
            "algorithm": closure["algorithm"],
            "count": closure["count"],
            "path_set_sha256": closure["path_set_sha256"],
            "content_sha256": closure["content_sha256"],
            "total_raw_bytes": closure["total_raw_bytes"],
        }
    except KeyError as error:
        _fail("freeze-manifest", "freeze manifest candidate closure is incomplete")
        raise AssertionError from error


def _tool_identities(value: Any) -> list[dict[str, Any]]:
    _plain(value, "tool_identities")
    if type(value) is dict:
        items = []
        for path, identity in value.items():
            if type(identity) is not dict:
                _fail("tool-identity", f"tool {path} identity is not an object")
            item = dict(identity)
            item["path"] = path
            items.append(item)
        value = items
    if type(value) is not list or len(value) not in {len(TOOL_PATHS), len(V4_TOOL_PATHS), len(V5_TOOL_PATHS)}:
        _fail("tool-identity", "current Phase 3 tool identities are incomplete")
    if len(value) == len(V5_TOOL_PATHS):
        expected_paths = V5_TOOL_PATHS
    elif len(value) == len(V4_TOOL_PATHS):
        expected_paths = V4_TOOL_PATHS
    else:
        expected_paths = TOOL_PATHS
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if type(item) is not dict or set(item) != {"path", "bytes", "sha256"}:
            _fail("tool-identity", f"tool identity {index} is not closed")
        path = _string(item["path"], f"tool identity {index}.path")
        if path not in expected_paths or path in seen:
            _fail("tool-identity", f"tool identity path {path} is unexpected or duplicated")
        seen.add(path)
        byte_count = _bounded_int(item["bytes"], f"tool identity {path}.bytes")
        digest = _sha(item["sha256"], f"tool identity {path}.sha256")
        normalized.append({"path": path, "bytes": byte_count, "sha256": digest})
    if [item["path"] for item in normalized] != list(expected_paths):
        _fail("tool-order", "tool identities must follow the preregistered order")
    return normalized


def _regular_bytes(path: Path, label: str) -> bytes:
    # Descriptor-based read from the filesystem root.  Every directory walk
    # and the final file open uses O_NOFOLLOW, so no check-then-path-open race
    # remains for package-relative tool identities.
    absolute = path.absolute()
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    parent = -1
    descriptor = -1
    try:
        parent = os.open(os.sep, flags | getattr(os, "O_DIRECTORY", 0))
        for component in absolute.parts[1:-1]:
            child = os.open(component, flags | getattr(os, "O_DIRECTORY", 0), dir_fd=parent)
            os.close(parent)
            parent = child
        name = absolute.parts[-1]
        info = os.stat(name, dir_fd=parent, follow_symlinks=False)
        if stat.S_ISLNK(info.st_mode):
            _fail("tool-symlink", f"{label} is a symlink")
        if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o644 or info.st_nlink != 1:
            _fail("tool-file", f"{label} is not a mode-0644 single-link file")
        if info.st_size > MAX_IDENTITY_BYTES:
            _fail("tool-file", f"{label} is oversized")
        descriptor = os.open(name, flags, dir_fd=parent)
    except GateBPreflightError:
        if parent >= 0:
            os.close(parent)
        raise
    except OSError as error:
        if parent >= 0:
            os.close(parent)
        if getattr(error, "errno", None) == getattr(os, "ELOOP", 40):
            raise GateBPreflightError("tool-symlink", f"{label} is a symlink") from error
        raise GateBPreflightError("tool-read", f"cannot open {label}") from error
    try:
        try:
            opened = os.fstat(descriptor)
            expected_identity = (info.st_dev, info.st_ino, info.st_size, info.st_mode, info.st_nlink, info.st_mtime_ns, info.st_ctime_ns)
            actual_identity = (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mode, opened.st_nlink, opened.st_mtime_ns, opened.st_ctime_ns)
            if actual_identity != expected_identity:
                _fail("tool-race", f"{label} changed before read")
            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = os.read(descriptor, min(1024 * 1024, MAX_IDENTITY_BYTES + 1 - total))
                if not chunk:
                    break
                chunks.append(chunk)
                total += len(chunk)
                if total > MAX_IDENTITY_BYTES:
                    _fail("tool-file", f"{label} grew beyond bound")
            raw = b"".join(chunks)
            after = os.fstat(descriptor)
            os.lseek(descriptor, 0, os.SEEK_SET)
            second_chunks: list[bytes] = []
            second_total = 0
            while True:
                chunk = os.read(descriptor, min(1024 * 1024, MAX_IDENTITY_BYTES + 1 - second_total))
                if not chunk:
                    break
                second_chunks.append(chunk)
                second_total += len(chunk)
                if second_total > MAX_IDENTITY_BYTES:
                    _fail("tool-file", f"{label} grew beyond bound on second read")
            second_raw = b"".join(second_chunks)
            second_after = os.fstat(descriptor)
            if second_raw != raw or (second_after.st_dev, second_after.st_ino, second_after.st_size, second_after.st_mode, second_after.st_nlink, second_after.st_mtime_ns, second_after.st_ctime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mode, after.st_nlink, after.st_mtime_ns, after.st_ctime_ns):
                _fail("tool-race", f"{label} changed between descriptor reads")
            after_identity = (after.st_dev, after.st_ino, after.st_size, after.st_mode, after.st_nlink, after.st_mtime_ns, after.st_ctime_ns)
            if after_identity != (info.st_dev, info.st_ino, len(raw), info.st_mode, info.st_nlink, info.st_mtime_ns, info.st_ctime_ns):
                _fail("tool-race", f"{label} changed during read")
            try:
                current = os.stat(name, dir_fd=parent, follow_symlinks=False)
            except OSError as error:
                raise GateBPreflightError("tool-race", f"cannot recheck {label}") from error
            current_identity = (current.st_dev, current.st_ino, current.st_size, current.st_mode, current.st_nlink, current.st_mtime_ns, current.st_ctime_ns)
            if current_identity != (info.st_dev, info.st_ino, len(raw), info.st_mode, info.st_nlink, info.st_mtime_ns, info.st_ctime_ns):
                _fail("tool-race", f"{label} changed after read")
            return raw
        except GateBPreflightError:
            raise
        except OSError as error:
            raise GateBPreflightError("tool-read", f"cannot read {label}") from error
    finally:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            finally:
                if parent >= 0:
                    os.close(parent)
        elif parent >= 0:
            os.close(parent)


def _validate_tools(root: Path, supplied: list[dict[str, Any]], manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    for identity in supplied:
        raw = _regular_bytes(root / identity["path"], identity["path"])
        if len(raw) != identity["bytes"] or hashlib.sha256(raw).hexdigest() != identity["sha256"]:
            _fail("tool-identity", f"current file identity differs for {identity['path']}")
    collections = (
        manifest.get("runtime_tool_identities"),
        manifest.get("exact_runtime_tool_identities"),
        manifest.get("provenance_tool_identities"),
    )
    if any(not isinstance(collection, list) for collection in collections):
        _fail("freeze-manifest", "freeze manifest tool identities are unavailable")
    recorded = [identity for collection in collections for identity in collection]
    normalized = []
    for identity in recorded:
        if not isinstance(identity, Mapping) or set(identity) != {"path", "mode", "bytes", "sha256"}:
            _fail("freeze-manifest", "freeze manifest runtime tool identity is malformed")
        normalized.append({key: identity[key] for key in ("path", "bytes", "sha256")})
    # The experiment-closure tool is a separate one-tool contract.  It is
    # validated below, but is never folded into the exact-runtime 19/20 count.
    if supplied != normalized:
        _fail("tool-identity", "caller tool identities differ from the canonical freeze manifest")
    return supplied


def _validate_experiment_closure_tools(root: Path, manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    closure = manifest.get("experiment_closure_tool_identities")
    if closure is None:
        return []
    if type(closure) is not list or [item.get("path") for item in closure if isinstance(item, Mapping)] != list(EXPERIMENT_CLOSURE_TOOL_PATHS):
        _fail("freeze-manifest", "experiment closure tool identity is not the closed contract")
    for identity in closure:
        if not isinstance(identity, Mapping) or set(identity) != {"path", "mode", "bytes", "sha256"}:
            _fail("freeze-manifest", "experiment closure tool identity is malformed")
        raw = _regular_bytes(root / identity["path"], identity["path"])
        if len(raw) != identity["bytes"] or hashlib.sha256(raw).hexdigest() != identity["sha256"]:
            _fail("tool-identity", f"current file identity differs for {identity['path']}")
    return [dict(item) for item in closure]


def _freeze_validator_identity(raw: bytes) -> dict[str, Any] | None:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise GateBPreflightError("freeze-manifest", "freeze manifest is not strict JSON") from error
    if not isinstance(value, Mapping):
        _fail("freeze-manifest", "freeze manifest is not an object")
    for field in ("runtime_tool_identities", "exact_runtime_tool_identities", "provenance_tool_identities"):
        identities = value.get(field)
        if isinstance(identities, list):
            for identity in identities:
                if isinstance(identity, Mapping) and identity.get("path") == FREEZE_SCRIPT_PATH:
                    return dict(identity)
    return None


def _load_freeze_module(root: Path, manifest_raw: bytes | None = None) -> Any:
    path = root / FREEZE_SCRIPT_PATH
    try:
        if manifest_raw is None:
            manifest_raw = _regular_bytes(root / FREEZE_MANIFEST_PATH, FREEZE_MANIFEST_PATH)
        expected = _freeze_validator_identity(manifest_raw)
        if expected is None or expected.get("mode") != 0o644 or type(expected.get("bytes")) is not int or type(expected.get("sha256")) is not str:
            _fail("freeze-manifest", "freeze manifest does not authenticate its validator")
        source = _regular_bytes(path, FREEZE_SCRIPT_PATH)
        if len(source) != expected["bytes"] or hashlib.sha256(source).hexdigest() != expected["sha256"]:
            _fail("freeze-manifest", "freeze validator bytes differ from the frozen identity")
        code = compile(source, str(path), "exec", dont_inherit=True, optimize=0)
        module_name = f"phase3_freeze_manifest_for_preflight_{id(root)}"
        module = types.ModuleType(module_name)
        module.__file__ = str(path)
        module.__package__ = ""
        module.__loader__ = None
        module.__spec__ = importlib.util.spec_from_loader(module_name, loader=None, origin=str(path))
        previous = sys.modules.get(module_name)
        sys.modules[module_name] = module
        try:
            exec(code, module.__dict__)
        except Exception:
            if previous is None:
                sys.modules.pop(module_name, None)
            else:
                sys.modules[module_name] = previous
            raise
        # The preflight owns the build-time Git seam.  Keep the freshly loaded
        # authenticated module's default overridable by a later authenticated
        # launcher, while this read-only tool remains pinned to /usr/bin/git.
        module.GIT_EXECUTABLE = GIT_EXECUTABLE
        return module
    except GateBPreflightError:
        raise
    except Exception as error:
        raise GateBPreflightError("freeze-manifest", "cannot load freeze-manifest validator") from error


def _validate_freeze_package(root: Path) -> tuple[Any, dict[str, Any]]:
    """Validate the canonical freeze and both receipts through freeze logic."""
    manifest_path = root / FREEZE_MANIFEST_PATH
    manifest_raw = _regular_bytes(manifest_path, FREEZE_MANIFEST_PATH)
    freeze = _load_freeze_module(root, manifest_raw)
    try:
        manifest = freeze.check_manifest(repo=REPOSITORY, package=root, path=manifest_path, manifest_raw=manifest_raw)
    except Exception as error:
        code = getattr(error, "code", "invalid")
        raise GateBPreflightError("freeze-manifest", f"canonical freeze validation failed: {code}") from error
    if not isinstance(manifest, dict):
        _fail("freeze-manifest", "canonical freeze validator did not return an object")
    allowed_schemas = {
        getattr(freeze, "SCHEMA", "ck.exp-0002.phase3.freeze-manifest-2"),
        getattr(freeze, "V3_SCHEMA", "ck.exp-0002.phase3.freeze-manifest-3"),
        getattr(freeze, "V4_SCHEMA", "ck.exp-0002.phase3.freeze-manifest-4"),
        getattr(freeze, "V5_SCHEMA", "ck.exp-0002.phase3.freeze-manifest-5"),
    }
    if manifest.get("schema") not in allowed_schemas:
        _fail("freeze-state", "canonical freeze manifest is not a supported successor schema")
    binaries = manifest.get("binaries")
    if not isinstance(binaries, dict) or set(binaries) != {"wsl2-x86_64", "ubuntu-24.04-x86_64"} or any(not isinstance(binaries[key], Mapping) or binaries[key].get("status") != "bound" for key in binaries):
        _fail("freeze-state", "both canonical binary slots must be bound")
    if manifest.get("execution_permitted") is not False:
        _fail("freeze-state", "canonical freeze manifest permits execution")
    readiness = manifest.get("readiness")
    if not isinstance(readiness, Mapping) or readiness.get("materialization_state") != "frozen" or readiness.get("execution_permitted") is not False or readiness.get("freeze_blockers") != []:
        _fail("freeze-state", "canonical freeze readiness is not an execution-disabled frozen package")
    receipt_directory = root / FREEZE_RECEIPT_DIR
    try:
        entries = {entry.name for entry in receipt_directory.iterdir()}
    except OSError as error:
        raise GateBPreflightError("receipt-layout", "cannot inspect the canonical receipt directory") from error
    if entries != set(FREEZE_RECEIPT_NAMES):
        _fail("receipt-layout", "canonical receipt directory must contain exactly WSL and native receipts")
    # check_manifest has already invoked phase3_build_receipt.validate_receipt
    # for both bound slots.  Requiring the exact paths here prevents a valid
    # sidecar from being silently substituted by an extra or renamed receipt.
    for name in FREEZE_RECEIPT_NAMES:
        path = receipt_directory / name
        try:
            info = path.lstat()
        except OSError as error:
            raise GateBPreflightError("receipt-layout", f"missing canonical receipt {name}") from error
        if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o644 or info.st_nlink != 1:
            _fail("receipt-layout", f"canonical receipt {name} is not a mode-0644 single-link file")
    return freeze, manifest


def _report(candidate: dict[str, Any], tools: list[dict[str, Any]], cases: list[dict[str, Any]], manifest: Mapping[str, Any]) -> dict[str, Any]:
    roles = {"development": 8, "held-out": 40, "controls": 12}
    dispatch = sum(case.get("dispatch_to_candidate", True) for case in cases)
    receipt_identities = {
        selector: {
            "path": slot["receipt_path"],
            "bytes": slot["receipt_bytes"],
            "sha256": slot["receipt_sha256"],
            "self_hash": slot["receipt_self_hash"],
        }
        for selector, slot in manifest["binaries"].items()
    }
    closure_tools = manifest.get("experiment_closure_tool_identities", [])
    closure_schema = manifest.get("experiment_closure_schema", "ck.exp-0002.phase3.experiment-closure-1")
    closure_bound = isinstance(closure_tools, list) and bool(closure_tools)
    v5_schema = "ck.exp-0002.phase3.freeze-manifest-5"
    exact_v5_bound = manifest.get("schema") == v5_schema and closure_bound
    runtime_tool_count = sum(len(manifest[field]) for field in ("runtime_tool_identities", "exact_runtime_tool_identities", "provenance_tool_identities"))
    return {
        "schema": SCHEMA,
        "evidence_schema": EVIDENCE_SCHEMA,
        "experiment_id": "EXP-0002",
        "phase_id": EXPECTED_PHASE,
        "candidate_profile_id": EXPECTED_PROFILE,
        "evidence": False,
        "gate_b_ready": False,
        "readiness": False,
        "review": False,
        "execution_permitted": False,
        "authorization_accepted": False,
        "technology_outcome": "none",
        "r3_activation": "inactive",
        "exact_runtime_closure": {
            "required": True,
            "required_schema": v5_schema,
            "status": "passed" if exact_v5_bound else "missing",
            "tool_count": runtime_tool_count,
            "closure_tool_count": len(closure_tools),
            "execution_permitted": False,
        },
        "experiment_closure_requirement": {
            "required": True,
            "schema": closure_schema,
            "ordinals": [0, 1, 2],
            "status": "missing",
            "execution_permitted": False,
        },
        "package": {
            "status": "Proposed",
            "lifecycle": "planned",
            "evidence_status": "open",
            "materialization": "development-unfrozen",
            "materialization_scope": "generated corpus and request materialization only",
            "not_evidence": True,
            "not_frozen": True,
            "freeze_field_note": "These are immutable Gate-A snapshot fields; the canonical freeze manifest supersedes them only for execution-package freeze state.",
        },
        "execution_package": {
            "freeze_state": "frozen",
            "freeze_schema": manifest["schema"],
            "manifest_path": FREEZE_MANIFEST_PATH,
            "manifest_sha256": manifest["manifest_sha256"],
            "predecessor_manifest_sha256": manifest["predecessor_manifest_sha256"],
            "candidate_source_commit": manifest["candidate_source_commit"],
            "execution_tool_source_commit": manifest["execution_tool_source_commit"],
            "predecessor_v1_manifest_sha256": manifest.get("predecessor_v1_manifest_sha256", "122b0a88bf553e95a887acebfe436d95218389e339ea5aa1f3c85d0f5186fef3"),
            "predecessor_v2_manifest_sha256": manifest.get("predecessor_manifest_sha256"),
            "source_snapshot_validation": {
                "status": "passed",
                "checker": "phase3_freeze_manifest.check_manifest",
                "ancestry_algorithm": "git merge-base --is-ancestor",
                "candidate_source_commit": manifest["candidate_source_commit"],
                "execution_tool_source_commit": manifest["execution_tool_source_commit"],
                "candidate_is_ancestor_of_execution_tools": True,
                "current_execution_tools_match_execution_tool_commit": True,
                "current_execution_tool_identity_count": runtime_tool_count,
            },
            "runtime_tool_identities": manifest["runtime_tool_identities"],
            "exact_runtime_tool_identities": manifest["exact_runtime_tool_identities"],
            "provenance_tool_identities": manifest["provenance_tool_identities"],
            "experiment_closure": {
                "schema": closure_schema,
                "tool_identities": closure_tools,
                "required_ordinals": [0, 1, 2],
                "status": "unbound",
                "execution_permitted": False,
                "normalization": "only request IDs and declared attempt/platform environment metadata",
                "global_status_precedence": ["failed", "inconclusive", "supported"],
            },
            "binary_slots": manifest["binaries"],
            "receipt_identities": receipt_identities,
            "readiness": manifest["readiness"],
            "note": "The preregistration pending-freeze fields are immutable Gate-A snapshot state; the canonical freeze manifest supersedes them only for execution-package freeze state.",
        },
        "candidate_identity": candidate,
        "tool_identities": tools,
        "accounting": {
            "case_adjudications": len(cases),
            "candidate_wire_requests": dispatch,
            "runner_preflight_adjudications": len(cases) - dispatch,
            "roles": roles,
            "processes_per_attempt": 3,
            "candidate_request_counts": {"development": 8, "held-out": 40, "controls": 9},
        },
        "checks": [
            {"name": "materialized-cases", "status": "passed"},
            {"name": "protocol-profile-tolerance-request-formula", "status": "passed"},
            {"name": "expected-prebound-candidate-identity", "status": "passed", "detail": "caller-supplied candidate closure matched the canonical freeze manifest"},
            {"name": "current-phase3-tool-identities", "status": "passed"},
            {"name": "candidate-to-execution-tool-ancestry", "status": "passed", "detail": "Git ancestry and both committed snapshots were checked by the freeze validator"},
            {"name": "current-execution-tool-snapshot", "status": "passed", "detail": manifest["execution_tool_source_commit"]},
            {"name": "freeze-manifest", "status": "passed", "detail": manifest["manifest_sha256"]},
            {"name": "exact-runtime-closure", "status": "passed" if exact_v5_bound else "missing", "detail": "v5 exact runtime tools are bound to the immutable execution snapshot" if exact_v5_bound else "v5 freeze successor is required by exact execution consumers"},
            {"name": "experiment-closure-adjudicator", "status": "missing", "detail": f"{closure_schema}; ordinals 0, 1, 2 required before any experiment outcome"},
            {"name": "gate-b-current-double-review", "status": "missing"},
        ],
        "missing_gate_b_items": [
            "current Gate B Double review of the frozen concrete package",
            *( ["v5 freeze successor required by exact execution consumers"] if not exact_v5_bound else [] ),
            *( ["new successor exact-runtime closure tool binding"] if not closure_bound else [] ),
            "experiment-wide closure of WSL ordinals 0/1 and native ordinal 2 using the frozen closure adjudicator",
            "Ben authorization for the exact attempts and native dispatch",
        ],
        "scope": "read-only readiness plumbing; validates the canonical frozen execution package but does not authorize or execute",
    }


def build_gate_b_preflight(
    package_root: str | os.PathLike[str],
    candidate_identity: Mapping[str, Any],
    tool_identities: Mapping[str, Any] | list[Mapping[str, Any]],
) -> dict[str, Any]:
    """Read and validate current Phase 3 materialization without execution."""
    _plain(candidate_identity, "candidate_identity")
    _plain(tool_identities, "tool_identities")
    if not isinstance(package_root, (str, os.PathLike)) or isinstance(package_root, (bytes, bytearray)):
        _fail("package-root", "package_root must be a path-like read-only root")
    root = Path(package_root)
    if not root.is_absolute():
        root = Path.cwd() / root
    root = Path(os.path.normpath(str(root)))
    try:
        if root.is_symlink():
            _fail("package-root", "package root is a symlink")
    except OSError as error:
        raise GateBPreflightError("package-root", "cannot inspect package root") from error
    freeze, manifest = _validate_freeze_package(root)
    candidate = _candidate_identity(candidate_identity)
    expected_candidate = _manifest_candidate_identity(manifest)
    if candidate != expected_candidate:
        _fail("candidate-identity", "caller candidate closure differs from the canonical freeze manifest")
    tools = _tool_identities(tool_identities)
    # The adapter owns the exact package/preregistration/manifest/protocol,
    # tolerance, request-ID, source, and 60-record checks.  Importantly, this
    # call only reads materialized bytes; it has no execution path.
    try:
        cases = load_materialized_cases(root)
    except Exception as error:
        if isinstance(error, GateBPreflightError):
            raise
        raise GateBPreflightError(getattr(error, "code", "package-preflight"), str(error)) from error
    if len(cases) != 60:
        _fail("accounting", "materialized package does not contain 60 cases")
    _validate_tools(root, tools, manifest)
    _validate_experiment_closure_tools(root, manifest)
    report = _report(candidate, tools, cases, manifest)
    # A final strict canonicalization check makes the returned mapping itself
    # the canonical non-evidence report, without exposing an execution handle.
    try:
        raw = json.dumps(report, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":"))
        canonical = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise GateBPreflightError("report", "preflight report is not canonical JSON") from error
    return canonical


def build_gate_b_preflight_bytes(
    package_root: str | os.PathLike[str],
    candidate_identity: Mapping[str, Any],
    tool_identities: Mapping[str, Any] | list[Mapping[str, Any]],
) -> bytes:
    report = build_gate_b_preflight(package_root, candidate_identity, tool_identities)
    raw = (json.dumps(report, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    if len(raw) > 256 * 1024:
        _fail("report", "preflight report exceeds bounded size")
    return raw


preflight = build_gate_b_preflight
gate_b_preflight = build_gate_b_preflight
preflight_bytes = build_gate_b_preflight_bytes

__all__ = ["SCHEMA", "GateBPreflightError", "build_gate_b_preflight", "build_gate_b_preflight_bytes", "preflight", "gate_b_preflight", "preflight_bytes", "TOOL_PATHS", "V4_TOOL_PATHS", "V5_TOOL_PATHS"]

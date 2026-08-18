"""Read-only Gate B readiness preflight for the Phase 3 package.

The preflight consumes the existing materialized package and caller-supplied
content identities.  It never runs Git, Cargo, a candidate, a shell, or an
environment probe, and it never creates a freeze manifest or changes package
state.  A successful call therefore reports readiness *blocked* by the
remaining Gate B bindings rather than authorizing execution.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
from pathlib import Path
from typing import Any, Mapping

from phase3_materialized_adapter import load_materialized_cases


SCHEMA = "ck.exp-0002.phase3.gate-b-preflight-1"
EVIDENCE_SCHEMA = "ck.exp-0002.phase3.evidence-proposed-1"
EXPECTED_ALGORITHM = "ck.phase3-candidate-source-build-closure.v1"
EXPECTED_CANDIDATE_COUNT = 47
EXPECTED_PATH_SHA256 = "10605701d02f117ff7ef2756004fbf53a475eb92fbc0616e139f919d7a8480dc"
EXPECTED_CONTENT_SHA256 = "21825e78c3286cf73d135f44be99eaea5214ce36b5fed6271dce096d364468e2"
EXPECTED_CANDIDATE_BYTES = 1_494_337
EXPECTED_PHASE = "phase3-semantic-band-conformance"
EXPECTED_PROFILE = "ck.provisional-r3-authored-conflict.semantic-band-1"
TOOL_PATHS = (
    "scripts/phase3_common.py",
    "scripts/phase3_oracle.py",
    "scripts/phase3_scorer.py",
    "scripts/phase3_runner.py",
    "scripts/phase3_receipt.py",
    "scripts/phase3_materialized_adapter.py",
    "scripts/phase3_evidence_contract.py",
    "scripts/phase3_gate_b_preflight.py",
)
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
    if type(value) is not list or len(value) != len(TOOL_PATHS):
        _fail("tool-identity", "current Phase 3 tool identities are incomplete")
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if type(item) is not dict or set(item) != {"path", "bytes", "sha256"}:
            _fail("tool-identity", f"tool identity {index} is not closed")
        path = _string(item["path"], f"tool identity {index}.path")
        if path not in TOOL_PATHS or path in seen:
            _fail("tool-identity", f"tool identity path {path} is unexpected or duplicated")
        seen.add(path)
        byte_count = _bounded_int(item["bytes"], f"tool identity {path}.bytes")
        digest = _sha(item["sha256"], f"tool identity {path}.sha256")
        normalized.append({"path": path, "bytes": byte_count, "sha256": digest})
    if [item["path"] for item in normalized] != list(TOOL_PATHS):
        _fail("tool-order", "tool identities must follow the preregistered order")
    return normalized


def _regular_bytes(path: Path, label: str) -> bytes:
    # Descriptor-based read: lstat and reject every symlink component, then
    # open without following symlinks and compare descriptor identity before,
    # during, and after the bounded read.  This keeps the preflight read-only
    # while closing the path/read TOCTOU window.
    for component in reversed(path.parents):
        try:
            if component.is_symlink():
                _fail("tool-symlink", f"{label} has a symlink component")
        except OSError as error:
            raise GateBPreflightError("tool-read", f"cannot inspect {label}") from error
    try:
        info = path.lstat()
    except OSError as error:
        raise GateBPreflightError("tool-missing", f"cannot inspect {label}") from error
    if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o644 or info.st_nlink != 1:
        _fail("tool-file", f"{label} is not a mode-0644 single-link file")
    if info.st_size > MAX_IDENTITY_BYTES:
        _fail("tool-file", f"{label} is oversized")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        if getattr(error, "errno", None) == getattr(os, "ELOOP", 40):
            raise GateBPreflightError("tool-symlink", f"{label} is a symlink") from error
        raise GateBPreflightError("tool-read", f"cannot open {label}") from error
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
    except OSError as error:
        raise GateBPreflightError("tool-read", f"cannot read {label}") from error
    finally:
        os.close(descriptor)
    after_identity = (after.st_dev, after.st_ino, after.st_size, after.st_mode, after.st_nlink, after.st_mtime_ns, after.st_ctime_ns)
    if after_identity != (info.st_dev, info.st_ino, len(raw), info.st_mode, info.st_nlink, info.st_mtime_ns, info.st_ctime_ns):
        _fail("tool-race", f"{label} changed during read")
    try:
        current = path.lstat()
    except OSError as error:
        raise GateBPreflightError("tool-race", f"cannot recheck {label}") from error
    current_identity = (current.st_dev, current.st_ino, current.st_size, current.st_mode, current.st_nlink, current.st_mtime_ns, current.st_ctime_ns)
    if current_identity != (info.st_dev, info.st_ino, len(raw), info.st_mode, info.st_nlink, info.st_mtime_ns, info.st_ctime_ns):
        _fail("tool-race", f"{label} changed after read")
    return raw


def _validate_tools(root: Path, supplied: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for identity in supplied:
        raw = _regular_bytes(root / identity["path"], identity["path"])
        if len(raw) != identity["bytes"] or hashlib.sha256(raw).hexdigest() != identity["sha256"]:
            _fail("tool-identity", f"current file identity differs for {identity['path']}")
    return supplied


def _report(candidate: dict[str, Any], tools: list[dict[str, Any]], cases: list[dict[str, Any]]) -> dict[str, Any]:
    roles = {"development": 8, "held-out": 40, "controls": 12}
    dispatch = sum(case.get("dispatch_to_candidate", True) for case in cases)
    return {
        "schema": SCHEMA,
        "evidence_schema": EVIDENCE_SCHEMA,
        "experiment_id": "EXP-0002",
        "phase_id": EXPECTED_PHASE,
        "candidate_profile_id": EXPECTED_PROFILE,
        "evidence": False,
        "gate_b_ready": False,
        "execution_permitted": False,
        "authorization_accepted": False,
        "technology_outcome": "none",
        "r3_activation": "inactive",
        "package": {
            "status": "Proposed",
            "lifecycle": "planned",
            "evidence_status": "open",
            "materialization": "development-unfrozen",
            "not_evidence": True,
            "not_frozen": True,
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
            {"name": "expected-prebound-candidate-identity", "status": "passed", "detail": "caller-supplied prebinding identity matched expected values; current-disk closure was not recomputed"},
            {"name": "current-phase3-tool-identities", "status": "passed"},
            {"name": "freeze-manifest", "status": "missing"},
            {"name": "gate-b-current-double-review", "status": "missing"},
        ],
        "missing_gate_b_items": [
            "freeze manifest and concrete freeze content identities",
            "independent current-disk candidate closure/freeze binding (not recomputed by this preflight)",
            "candidate binary identity",
            "toolchain/compiler identity",
            "exact build and run commands and flags",
            "frozen platform selectors and environment/workflow identity",
            "current Gate B Double review of the frozen concrete package",
            "Ben authorization for the exact attempts and native dispatch",
        ],
        "scope": "read-only readiness plumbing; no freeze, authorization, or execution",
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
    candidate = _candidate_identity(candidate_identity)
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
    _validate_tools(root, tools)
    report = _report(candidate, tools, cases)
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

__all__ = ["SCHEMA", "GateBPreflightError", "build_gate_b_preflight", "build_gate_b_preflight_bytes", "preflight", "gate_b_preflight", "preflight_bytes", "TOOL_PATHS"]

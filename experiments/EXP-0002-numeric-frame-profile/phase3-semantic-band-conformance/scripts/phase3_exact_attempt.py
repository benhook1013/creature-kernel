"""One-shot Phase 3 exact-attempt orchestration.

The exact attempt is intentionally a thin, fail-closed composition boundary.
The semantic/package, authority, custody, transport, adjudication, evidence,
and publication modules remain owners of their respective contracts.  This
module only fixes their order and the attempt accounting:

* all non-executing checks and all work locations are prepared first;
* the exclusive publication reservation is acquired before a candidate can be
  launched;
* exactly one fresh transport session is made for each ordered role;
* transport/process failures become incomplete process observations and do
  not prevent a later role from being attempted; and
* the complete 60-case adjudication is retained before result/receipt/index
  construction and reserved publication.

No candidate path, arbitrary argv/environment, process count, retry policy, or
corpus path is accepted from the caller.  Dependencies are injectable only so
the sequencing boundary can be tested with in-memory fakes; production
defaults are the existing Phase 3 modules.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import inspect
import json
import math
import os
from pathlib import Path
import platform as _platform
import stat
import sys
import sysconfig
from types import MappingProxyType
from typing import Any, Callable, Mapping, Sequence

import phase3_exact_adjudicator as adjudicator
import phase3_exact_authority as authority
import phase3_exact_custody as custody
import phase3_exact_fp_observer as fp_observer
import phase3_exact_publication as publication
import phase3_exact_transport as transport
import phase3_evidence_contract as evidence_contract
import phase3_gate_b_preflight as gate_b_preflight


PHASE_ID = "exp-0002-phase3-semantic-band-conformance-001"
EXPERIMENT_ID = "EXP-0002"
CANDIDATE_PROFILE_ID = "ck.provisional-r3-authored-conflict.semantic-band-1"
ROLE_ORDER = ("development", "held-out", "controls")
ROLE_CASE_COUNTS = MappingProxyType({"development": 8, "held-out": 40, "controls": 12})
ROLE_REQUEST_COUNTS = MappingProxyType({"development": 8, "held-out": 40, "controls": 9})
PLATFORM_ORDINALS = MappingProxyType({
    "wsl2-x86_64": frozenset({0, 1}),
    "ubuntu-24.04-x86_64": frozenset({2}),
})
TARGET = "x86_64-unknown-linux-gnu"
# These values are fixed by the exact-attempt contract.  In particular, a
# caller cannot smuggle a wrapper command or host environment into transport.
CANDIDATE_ARGV0 = "exp-0002-r3-authored-conflict-candidate"
CANDIDATE_ENVIRONMENT = MappingProxyType({"LANG": "C", "LC_ALL": "C"})
EXPECTED_FP = fp_observer.FPExpectation(
    x87_rounding_mode="nearest",
    mxcsr_rounding_mode="nearest",
    ftz=False,
    daz=False,
)

# v3 does not bind this contract and is therefore not execution-admissible.
# The orchestrator-owned successor freeze must authenticate exact per-selector
# patch versions and invocation/module-loading facts before this boundary can
# reserve a slot.  Nothing here derives an expected value from ambient ``sys``.
PYTHON_RUNTIME_CONTRACT_FIELD = "exact_python_runtime_contract"
PYTHON_RUNTIME_CONTRACT_SCHEMA = "ck.exp-0002.phase3.python-runtime-contract-1"
PYTHON_RUNTIME_CONTRACT_KEYS = frozenset({"selector", "implementation", "version", "invocation", "module_loading", "entrypoint"})

MAX_RECORD_BYTES = 64 * 1024
MAX_TOOL_IDENTITIES = 32
MAX_ROOT_BYTES = 4096
MAX_OUTPUT_IDS = 256
MAX_OUTPUT_ID_BYTES = 128
MALFORMED_OUTPUT_ID = "malformed-response"
EXTRA_OUTPUT_ID = "extra-response"
MISMATCH_OUTPUT_ID = "mismatched-response"
TRAILING_OUTPUT_ID = "trailing-output"
# Keep this in lockstep with the exact transport/evidence contracts.  It is
# deliberately equal to the larger of the two frozen v2 binary slots.
MAX_EXECUTABLE_BYTES = 100_945_304


class ExactAttemptError(ValueError):
    """Stable fail-closed error from orchestration/preflight."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = str(code)
        self.detail = str(detail).replace("\x00", "?").replace("\n", " ").replace("\r", "")[:512]
        super().__init__(f"{self.code}: {self.detail}" if self.detail else self.code)


def _fail(code: str, detail: str = "") -> None:
    raise ExactAttemptError(code, detail)


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical_record(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > MAX_RECORD_BYTES or not raw.endswith(b"\n"):
        _fail("record", f"{label} is absent, oversized, or not LF terminated")
    pairs: list[tuple[str, Any]] = []

    def duplicate_guard(items: list[tuple[str, Any]]) -> dict[str, Any]:
        seen: dict[str, Any] = {}
        for key, value in items:
            if key in seen:
                _fail("duplicate-json-key", f"{label} contains duplicate {key}")
            seen[key] = value
        return seen

    del pairs
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=duplicate_guard,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except ExactAttemptError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, TypeError, ValueError) as error:
        raise ExactAttemptError("record", f"{label} is malformed strict JSON") from error
    if type(value) is not dict:
        _fail("record", f"{label} must be an object")
    try:
        canonical = (json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise ExactAttemptError("record", f"{label} cannot be canonicalized") from error
    if canonical != raw:
        _fail("record", f"{label} is not canonical JSON")
    return value


def _bounded_bytes(value: Any, label: str, limit: int = MAX_RECORD_BYTES) -> bytes:
    if type(value) is not bytes or not value or len(value) > limit:
        _fail("record", f"{label} is not bounded bytes")
    return value


def _attempt_id(value: Any) -> str:
    if type(value) is not str or adjudicator.ATTEMPT_RE.fullmatch(value) is None:
        _fail("attempt-id", "attempt_id violates the fixed attempt-ID form")
    return value


def _root_path(value: Path | str, label: str) -> Path:
    if not isinstance(value, (Path, str)):
        _fail("root", f"{label} must be a path")
    path = Path(value)
    if not path.is_absolute() or len(os.fsencode(str(path))) > MAX_ROOT_BYTES:
        _fail("root", f"{label} must be bounded absolute path")
    if any(part in {"", ".", ".."} or "\\" in part or "\x00" in part for part in path.parts[1:]):
        _fail("root", f"{label} has unsafe path components")
    return path


def _reject_symlink_components(path: Path) -> None:
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        try:
            if current.is_symlink():
                _fail("root", f"{path} contains a symlink component")
        except OSError as error:
            raise ExactAttemptError("root", f"cannot inspect {path}") from error


def _ensure_directory(path: Path, label: str) -> None:
    """Create one explicitly scoped directory and verify its type/mode."""
    _reject_symlink_components(path.parent)
    try:
        existed = path.exists()
        path.mkdir(mode=0o755, parents=False, exist_ok=True)
        info = path.lstat()
    except OSError as error:
        raise ExactAttemptError("root", f"cannot create {label}") from error
    if not stat.S_ISDIR(info.st_mode):
        _fail("root", f"{label} is not a directory")
    # Existing private roots (0700) are valid; newly-created locations are
    # normalized to the fixed non-world-writable workspace mode.
    if not existed:
        try:
            os.chmod(path, 0o755, follow_symlinks=False)
            info = path.lstat()
        except OSError as error:
            raise ExactAttemptError("root", f"cannot normalize {label} mode") from error
    if stat.S_IMODE(info.st_mode) & 0o022:
        _fail("root", f"{label} is group/world-writable")


def _create_directory(path: Path, label: str) -> None:
    """Create a fresh attempt-scoped directory; never reuse stale work."""
    _reject_symlink_components(path.parent)
    try:
        path.mkdir(mode=0o755, parents=False, exist_ok=False)
        os.chmod(path, 0o755, follow_symlinks=False)
        info = path.lstat()
    except FileExistsError as error:
        raise ExactAttemptError("work-collision", f"{label} already exists") from error
    except OSError as error:
        raise ExactAttemptError("root", f"cannot create {label}") from error
    if not stat.S_ISDIR(info.st_mode) or stat.S_IMODE(info.st_mode) & 0o022:
        _fail("root", f"{label} is not a private directory")


def _open_anchored_directory(path: Path, label: str) -> tuple[int, dict[str, int]]:
    """Open a directory by descriptor-walk and retain its identity."""
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    fd = -1
    try:
        fd = os.open(os.sep, flags)
        for component in path.parts[1:]:
            next_fd = os.open(component, flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        info = os.fstat(fd)
        if not stat.S_ISDIR(info.st_mode) or stat.S_IMODE(info.st_mode) & 0o022:
            _fail("root", f"{label} is not a private directory")
        # Keep the raw stat for the descriptor/path safety checks above, but
        # expose the same stable directory identity representation used by
        # exact transport.  Directory size and link count are mutable as
        # unrelated children come and go, so transport intentionally records
        # both as zero for cwd_pre/cwd_post comparisons.
        identity = transport.DescriptorIdentity.from_stat(info)
        normalized = transport.DescriptorIdentity(identity.device, identity.inode, identity.mode, 0, 0)
        return fd, normalized.to_dict()
    except ExactAttemptError:
        if fd >= 0:
            os.close(fd)
        raise
    except OSError as error:
        if fd >= 0:
            os.close(fd)
        raise ExactAttemptError("root", f"cannot open {label}") from error


def _prepare_work_locations(output_root: Path, work_root: Path, attempt_id: str) -> tuple[Path, dict[str, Path], dict[str, int], dict[str, dict[str, int]]]:
    """Create post-reservation attempt locations and anchored role descriptors."""
    attempt_work = work_root / attempt_id
    _create_directory(attempt_work, "attempt work root")
    role_dirs: dict[str, Path] = {}
    role_fds: dict[str, int] = {}
    role_identities: dict[str, dict[str, int]] = {}
    try:
        for role in ROLE_ORDER:
            role_path = attempt_work / role
            _create_directory(role_path, f"{role} work root")
            role_dirs[role] = role_path
            role_fds[role], role_identities[role] = _open_anchored_directory(role_path, f"{role} work root")
        custody_path = attempt_work / "custody"
        _create_directory(custody_path, "custody work root")
        return custody_path, role_dirs, role_fds, role_identities
    except Exception:
        for fd in role_fds.values():
            try:
                os.close(fd)
            except OSError:
                pass
        raise


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail("record", f"{label} must be a mapping")
    return value


def _record_hash(raw: bytes, label: str) -> str:
    _canonical_record(raw, label)
    return _sha256(raw)


def _read_candidate_descriptor(fd: int, expected_size: int, expected_sha256: str) -> bytes:
    """Read the already-custodied sealed descriptor without using a path."""
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size != expected_size:
            _fail("custody", "candidate descriptor identity differs from custody")
        if expected_size > MAX_EXECUTABLE_BYTES:
            _fail("custody", "candidate descriptor exceeds transport bound")
        raw = os.pread(fd, expected_size, 0)
        after = os.fstat(fd)
    except ExactAttemptError:
        raise
    except OSError as error:
        raise ExactAttemptError("custody", "candidate descriptor cannot be read") from error
    if info != after or len(raw) != expected_size or _sha256(raw) != expected_sha256:
        _fail("custody", "candidate descriptor changed or hash differs")
    return raw


def _validate_selected_binary_compatibility(
    freeze: Mapping[str, Any], platform_selector: str, custody_value: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind the selected frozen binary slot to static custody before reserve."""
    binaries = freeze.get("binaries")
    if not isinstance(binaries, Mapping) or platform_selector not in binaries:
        _fail("custody", "selected platform has no frozen binary slot")
    slot = binaries[platform_selector]
    if not isinstance(slot, Mapping) or slot.get("status") != "bound":
        _fail("custody", "selected frozen binary slot is not bound")
    frozen = slot.get("binary_identity")
    if not isinstance(frozen, Mapping) or set(frozen) != {"bytes", "mode", "sha256"}:
        _fail("custody", "selected frozen binary identity is malformed")
    size = frozen["bytes"]
    digest = frozen["sha256"]
    mode = frozen["mode"]
    if type(size) is not int or isinstance(size, bool) or size <= 0 or size > MAX_EXECUTABLE_BYTES:
        _fail("custody", "selected frozen binary size exceeds exact transport bound")
    if type(mode) is not int or stat.S_IMODE(mode) != 0o755 or not stat.S_ISREG(mode):
        _fail("custody", "selected frozen binary mode is not regular executable 0755")
    if type(digest) is not str or len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        _fail("custody", "selected frozen binary hash is malformed")
    candidate = custody_value.get("candidate")
    if not isinstance(candidate, Mapping) or set(candidate) < {"bytes", "mode", "sha256"}:
        _fail("custody", "static custody did not retain selected candidate identity")
    if {key: candidate[key] for key in ("bytes", "mode", "sha256")} != {"bytes": size, "mode": mode, "sha256": digest}:
        _fail("custody", "static custody candidate differs from selected frozen binary slot")
    return {"bytes": size, "mode": mode, "sha256": digest}


def _freeze_identity(raw: bytes) -> tuple[dict[str, Any], str]:
    value = _canonical_record(raw, "freeze manifest")
    manifest_hash = value.get("manifest_sha256")
    if type(manifest_hash) is not str or len(manifest_hash) != 64 or any(char not in "0123456789abcdef" for char in manifest_hash):
        _fail("freeze", "freeze manifest has no lowercase self-hash")
    return value, manifest_hash


def _validate_frozen_runtime_contract(freeze: Mapping[str, Any], selector: str) -> Mapping[str, Any]:
    """Require the authenticated successor runtime contract for one selector."""
    value = freeze.get(PYTHON_RUNTIME_CONTRACT_FIELD)
    if not isinstance(value, Mapping):
        _fail("runtime-contract", "the supplied freeze does not bind exact Python runtime facts; v3 remains execution-disabled")
    if set(value) != {"schema", "platforms"} or value.get("schema") != PYTHON_RUNTIME_CONTRACT_SCHEMA:
        _fail("runtime-contract", "freeze Python runtime contract has the wrong schema")
    platforms = value.get("platforms")
    if not isinstance(platforms, Mapping) or set(platforms) != set(PLATFORM_ORDINALS):
        _fail("runtime-contract", "freeze Python runtime contract must bind every platform selector")
    selected = platforms.get(selector)
    if not isinstance(selected, Mapping) or set(selected) != PYTHON_RUNTIME_CONTRACT_KEYS:
        _fail("runtime-contract", f"freeze Python runtime contract is incomplete for {selector}")
    if selected.get("selector") != selector:
        _fail("runtime-contract", f"freeze Python runtime contract selector is not {selector}")
    implementation = selected.get("implementation")
    version = selected.get("version")
    invocation = selected.get("invocation")
    module_loading = selected.get("module_loading")
    entrypoint = selected.get("entrypoint")
    version_parts = version.split(".") if type(version) is str else []
    if (
        type(implementation) is not str or not implementation
        or type(version) is not str or not version
        or len(version_parts) != 3
        or any(not part or any(char not in "0123456789" for char in part) for part in version_parts)
    ):
        _fail("runtime-contract", f"freeze Python runtime contract lacks an exact patch version for {selector}")
    if type(invocation) is not list or not invocation or any(type(item) is not str or not item for item in invocation):
        _fail("runtime-contract", f"freeze Python invocation is not a canonical non-empty argv for {selector}")
    if type(module_loading) is not str or not module_loading or type(entrypoint) is not str or not entrypoint:
        _fail("runtime-contract", f"freeze Python module-loading contract is incomplete for {selector}")
    return selected


def _normalize_tools(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail("tools", "tool identities must be an ordered sequence")
    if len(value) > MAX_TOOL_IDENTITIES:
        _fail("tools", "tool identity list exceeds bound")
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, Mapping) or set(item) != {"path", "bytes", "sha256"}:
            _fail("tools", f"tool identity {index} is not closed")
        path = item["path"]
        if type(path) is not str or not path or path.startswith("/") or "\\" in path or any(part in {"", ".", ".."} for part in path.split("/")):
            _fail("tools", f"tool identity {index} path is unsafe")
        if path in seen:
            _fail("tools", f"tool identity {path} is duplicated")
        seen.add(path)
        if type(item["bytes"]) is not int or isinstance(item["bytes"], bool) or not 0 < item["bytes"] <= 16 * 1024 * 1024:
            _fail("tools", f"tool identity {path} byte count is invalid")
        digest = item["sha256"]
        if type(digest) is not str or len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            _fail("tools", f"tool identity {path} digest is invalid")
        normalized.append({"path": path, "bytes": item["bytes"], "sha256": digest})
    return normalized


def _freeze_tool_collection(freeze: Mapping[str, Any], field: str) -> list[dict[str, Any]]:
    declared = freeze.get(field)
    if not isinstance(declared, list) or not declared:
        _fail("tools", f"freeze {field} is malformed or absent")
    expected: list[dict[str, Any]] = []
    for index, item in enumerate(declared):
        if not isinstance(item, Mapping) or set(item) != {"path", "mode", "bytes", "sha256"} or item.get("mode") != 0o644:
            _fail("tools", f"freeze {field}[{index}] is malformed")
        expected.append({key: item[key] for key in ("path", "bytes", "sha256")})
    return expected


def _validate_tool_binding(freeze: Mapping[str, Any], supplied: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Validate the full frozen runtime closure and project core tools.

    The preflight boundary receives one unambiguous closure in canonical
    runtime/exact-runtime/provenance order.  Evidence is intentionally given
    only the eight core runtime identities required by its public contract.
    """
    runtime = _freeze_tool_collection(freeze, "runtime_tool_identities")
    exact = _freeze_tool_collection(freeze, "exact_runtime_tool_identities")
    provenance = _freeze_tool_collection(freeze, "provenance_tool_identities")
    expected = [*runtime, *exact, *provenance]
    if supplied != expected:
        _fail("tools", f"supplied tool identities differ from the canonical {len(expected)}-tool freeze closure")
    return runtime


def _authenticated_tool_count(freeze: Mapping[str, Any]) -> int:
    """Count execution/provenance tools; the experiment closure is separate."""
    return sum(len(_freeze_tool_collection(freeze, field)) for field in (
        "runtime_tool_identities", "exact_runtime_tool_identities", "provenance_tool_identities",
    ))


def _normalize_report_tools(value: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        _fail("preflight", f"preflight {label} is malformed")
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping) or not {"path", "bytes", "sha256"} <= set(item):
            _fail("preflight", f"preflight {label}[{index}] is malformed")
        normalized.append({key: item[key] for key in ("path", "bytes", "sha256")})
    return _normalize_tools(normalized)


def _validate_source_snapshot_attestation(
    freeze: Mapping[str, Any], execution_package: Mapping[str, Any], supplied_tools: Sequence[Mapping[str, Any]],
) -> None:
    """Bind Gate-B's current source snapshot attestation to the freeze."""
    candidate_commit = freeze.get("candidate_source_commit")
    execution_commit = freeze.get("execution_tool_source_commit")
    if type(candidate_commit) is not str or type(execution_commit) is not str:
        _fail("preflight", "authenticated freeze is missing source commits")
    if execution_package.get("candidate_source_commit") != candidate_commit or execution_package.get("execution_tool_source_commit") != execution_commit:
        _fail("preflight", "execution package source commits differ from the authenticated freeze")
    snapshot = execution_package.get("source_snapshot_validation")
    expected_keys = {
        "status", "checker", "ancestry_algorithm", "candidate_source_commit",
        "execution_tool_source_commit", "candidate_is_ancestor_of_execution_tools",
        "current_execution_tools_match_execution_tool_commit", "current_execution_tool_identity_count",
    }
    if not isinstance(snapshot, Mapping) or set(snapshot) != expected_keys:
        _fail("preflight", "source snapshot validation is missing or not the current closed schema")
    if (
        snapshot["status"] != "passed"
        or snapshot["checker"] != "phase3_freeze_manifest.check_manifest"
        or snapshot["ancestry_algorithm"] != "git merge-base --is-ancestor"
        or snapshot["candidate_source_commit"] != candidate_commit
        or snapshot["execution_tool_source_commit"] != execution_commit
        or snapshot["candidate_is_ancestor_of_execution_tools"] is not True
        or snapshot["current_execution_tools_match_execution_tool_commit"] is not True
        or type(snapshot["current_execution_tool_identity_count"]) is not int
        or snapshot["current_execution_tool_identity_count"] != _authenticated_tool_count(freeze)
        or len(supplied_tools) != _authenticated_tool_count(freeze)
    ):
        _fail("preflight", f"source snapshot validation does not attest the authenticated {_authenticated_tool_count(freeze)}-tool closure")


def _read_bounded_text(path: str, limit: int = 4096) -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")[:limit]
    except OSError:
        return "unavailable"


def _actual_platform_selector() -> str:
    release = (_platform.release() or "").casefold()
    if "microsoft" in release or "wsl" in release:
        return "wsl2-x86_64"
    os_release = _read_bounded_text("/etc/os-release", 4096)
    fields = {}
    for line in os_release.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            fields[key] = value.strip().strip('"')
    if fields.get("ID") == "ubuntu" and fields.get("VERSION_ID") == "24.04":
        return "ubuntu-24.04-x86_64"
    return "native-unregistered-x86_64"


def _mount_for_path(path: Path) -> tuple[str, str]:
    """Return the observed filesystem type and mountpoint for one path."""
    raw = _read_bounded_text("/proc/self/mountinfo", 256 * 1024)
    if raw == "unavailable":
        _fail("platform", "mountinfo is unavailable")
    target = str(path)
    best: tuple[int, str, str] | None = None
    for line in raw.splitlines():
        fields = line.split(" - ", 1)
        if len(fields) != 2:
            continue
        left, right = fields
        left_fields = left.split()
        right_fields = right.split()
        if len(left_fields) < 5 or not right_fields:
            continue
        mountpoint = left_fields[4].replace("\\040", " ").replace("\\011", "\t")
        if target == mountpoint or target.startswith(mountpoint.rstrip("/") + "/"):
            if best is None or len(mountpoint) > best[0]:
                best = (len(mountpoint), right_fields[0], mountpoint)
    if best is None:
        _fail("platform", f"no mountinfo entry for {path}")
    return best[1], best[2]


def _location_observation(path: Path | None, label: str) -> dict[str, Any] | None:
    if path is None:
        return None
    path = Path(path)
    if not path.is_absolute():
        _fail("platform", f"{label} is not absolute")
    _reject_symlink_components(path)
    try:
        info = path.lstat()
    except OSError as error:
        raise ExactAttemptError("platform", f"{label} identity unavailable") from error
    if stat.S_ISLNK(info.st_mode):
        _fail("platform", f"{label} is symlinked")
    if not stat.S_ISDIR(info.st_mode):
        _fail("platform", f"{label} is not a directory")
    filesystem, mount = _mount_for_path(path)
    return {
        "path": str(path), "kind": "directory", "device": int(info.st_dev),
        "inode": int(info.st_ino), "mode": int(info.st_mode), "size": int(info.st_size),
        "nlink": int(info.st_nlink), "filesystem": filesystem, "mount": mount,
    }


def _load_frozen_build_facts(package_root: Path, freeze: Mapping[str, Any], selector: str) -> dict[str, str]:
    """Read and bind the selected frozen receipt without inventing workflow facts."""
    binaries = freeze.get("binaries")
    build = freeze.get("build")
    if not isinstance(binaries, Mapping) or not isinstance(build, Mapping) or selector not in binaries:
        _fail("platform", "frozen selected build facts are unavailable")
    slot = binaries[selector]
    if not isinstance(slot, Mapping):
        _fail("platform", "frozen selected binary slot is malformed")
    receipt_path = slot.get("receipt_path") if isinstance(slot, Mapping) else None
    if type(receipt_path) is not str or receipt_path.startswith("/") or ".." in Path(receipt_path).parts:
        _fail("platform", "frozen receipt path is unsafe")
    receipt = package_root / receipt_path
    parts = receipt.parts
    if not receipt.is_absolute() or len(parts) < 2:
        _fail("platform", "frozen receipt path is not absolute after package binding")
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    parent_fd = -1
    fd = -1
    try:
        parent_fd = os.open(os.sep, flags)
        for component in parts[1:-1]:
            child_fd = os.open(component, flags, dir_fd=parent_fd)
            os.close(parent_fd)
            parent_fd = child_fd
        name = parts[-1]
        path_before = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if stat.S_ISLNK(path_before.st_mode) or not stat.S_ISREG(path_before.st_mode) or path_before.st_nlink != 1:
            _fail("platform", "frozen selected receipt is not a regular single-link file")
        fd = os.open(name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0), dir_fd=parent_fd)
        before = os.fstat(fd)
        expected_identity = (path_before.st_dev, path_before.st_ino, path_before.st_mode, path_before.st_nlink, path_before.st_size, path_before.st_mtime_ns, path_before.st_ctime_ns)
        opened_identity = (before.st_dev, before.st_ino, before.st_mode, before.st_nlink, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
        if opened_identity != expected_identity:
            _fail("platform", "frozen selected receipt changed before read")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(fd, min(1024 * 1024, MAX_RECORD_BYTES + 1 - total))
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_RECORD_BYTES:
                _fail("platform", "frozen selected receipt exceeds record bound")
            chunks.append(chunk)
        raw = b"".join(chunks)
        after = os.fstat(fd)
        path_after = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        after_identity = (after.st_dev, after.st_ino, after.st_mode, after.st_nlink, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
        path_identity = (path_after.st_dev, path_after.st_ino, path_after.st_mode, path_after.st_nlink, path_after.st_size, path_after.st_mtime_ns, path_after.st_ctime_ns)
        if after_identity != expected_identity or path_identity != after_identity or total != path_before.st_size:
            _fail("platform", "frozen selected receipt changed while read")
    except ExactAttemptError:
        raise
    except OSError as error:
        raise ExactAttemptError("platform", "frozen selected receipt is unavailable") from error
    finally:
        if fd >= 0:
            os.close(fd)
        if parent_fd >= 0:
            os.close(parent_fd)
    if type(slot.get("receipt_bytes")) is not int or slot["receipt_bytes"] <= 0 or len(raw) != slot["receipt_bytes"]:
        _fail("platform", "selected receipt byte count differs from frozen identity")
    if _sha256(raw) != slot.get("receipt_sha256"):
        _fail("platform", "selected receipt bytes differ from frozen identity")
    receipt = _canonical_record(raw, "selected build receipt")
    if receipt.get("receipt_sha256") != slot.get("receipt_self_hash"):
        _fail("platform", "selected receipt self-hash differs from frozen identity")
    receipt_build = receipt.get("build")
    if not isinstance(receipt_build, Mapping):
        _fail("platform", "selected receipt build facts are unavailable")
    observation = receipt_build.get("platform_observation")
    toolchain = receipt_build.get("toolchain")
    if not isinstance(observation, Mapping) or not isinstance(toolchain, Mapping):
        _fail("platform", "selected receipt platform/toolchain facts are unavailable")
    required = ("runner_os", "image_os", "image_version")
    if any(type(observation.get(key)) is not str or not observation.get(key) for key in required):
        _fail("platform", "selected receipt workflow facts are incomplete")
    if type(receipt_build.get("platform_role")) is not str or not receipt_build["platform_role"]:
        _fail("platform", "selected receipt platform role is incomplete")
    for key in ("rust_toolchain", "rustc"):
        if type(toolchain.get(key)) is not str or not toolchain.get(key):
            _fail("platform", "selected receipt compiler facts are incomplete")
    return {
        "source": "frozen-build-receipt", "selector": selector,
        "receipt_sha256": str(slot["receipt_sha256"]), "receipt_self_hash": str(slot["receipt_self_hash"]),
        "platform_role": str(receipt_build.get("platform_role", "")),
        "runner_os": observation["runner_os"], "image_os": observation["image_os"],
        "image_version": observation["image_version"], "toolchain": toolchain["rust_toolchain"],
        "compiler": toolchain["rustc"],
    }


def _platform_observation(
    requested_selector: str,
    *, package_root: Path, output_root: Path, work_root: Path,
    custody_root: Path | None = None, role_dirs: Mapping[str, Path] | None = None,
    frozen_build: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Return descriptor/path-specific runtime facts and frozen build facts."""
    machine = _platform.machine()
    uname = _platform.uname()
    selector = _actual_platform_selector()
    if selector != requested_selector or machine != "x86_64":
        _fail("platform", "actual platform does not match requested x86_64 selector")
    cpu_model = _platform.processor()
    if not cpu_model:
        _fail("platform", "CPU model observation is unavailable")
    flags: list[str] = []
    cpuinfo = _read_bounded_text("/proc/cpuinfo", 64 * 1024)
    for line in cpuinfo.splitlines():
        if line.casefold().startswith(("flags", "features")) and ":" in line:
            flags = [item for item in line.split(":", 1)[1].split() if item][:128]
            break
    if not flags:
        _fail("platform", "CPU feature observation is unavailable")
    os_release = _read_bounded_text("/etc/os-release", 4096).strip()
    if os_release == "unavailable":
        _fail("platform", "OS release observation is unavailable")
    if requested_selector == "ubuntu-24.04-x86_64" and ("ID=ubuntu" not in os_release or "VERSION_ID=24.04" not in os_release):
        _fail("platform", "native selector requires Ubuntu 24.04 runtime facts")
    if requested_selector == "wsl2-x86_64" and "microsoft" not in (uname.release or "").casefold() and "wsl" not in (uname.release or "").casefold():
        _fail("platform", "WSL selector requires WSL kernel facts")
    locations = {
        "package": _location_observation(package_root, "package root"),
        "output": _location_observation(output_root, "output root"),
        "work": _location_observation(work_root, "work root"),
        "custody": _location_observation(custody_root, "custody root"),
        "roles": {role: _location_observation((role_dirs or {}).get(role), f"{role} role root") for role in ROLE_ORDER},
    }
    if requested_selector == "wsl2-x86_64":
        for name, item in (("package", locations["package"]), ("output", locations["output"]), ("work", locations["work"]), ("custody", locations["custody"])):
            if item is not None and not str(item["path"]).startswith("/home/"):
                _fail("platform", f"WSL {name} location is outside the declared /home boundary")
        for role, item in locations["roles"].items():
            if item is not None and not str(item["path"]).startswith("/home/"):
                _fail("platform", f"WSL {role} role location is outside the declared /home boundary")
    if frozen_build is None:
        _fail("platform", "frozen build receipt facts are required")
    runtime = {
        "implementation": sys.implementation.name,
        "version": sys.version.split()[0],
        "executable": str(Path(sys.executable).resolve()),
        "python_version": _platform.python_version(),
        "platform": sysconfig.get_platform(),
        "libc": " ".join(item for item in _platform.libc_ver() if item) or "unknown",
    }
    if any(not value or value == "unknown" for value in runtime.values()):
        _fail("platform", "Python runtime facts are incomplete")
    return {
        "selector": selector, "cpu_model": cpu_model[:1024], "cpu_features": flags,
        "architecture": machine, "kernel_or_wsl": (uname.release or "")[:1024],
        "os_release": os_release[:1024], "filesystem": locations["package"]["filesystem"],
        "mount_context": locations["package"]["mount"],
        "workflow_runner": f"build-receipt:{frozen_build['runner_os']}",
        "workflow_image": f"build-receipt:{frozen_build['image_os']}:{frozen_build['image_version']}",
        "toolchain": f"build-receipt:{frozen_build['toolchain']}",
        "compiler": f"build-receipt:{frozen_build['compiler']}",
        "locations": locations, "runtime": runtime,
        "build_receipt": dict(frozen_build),
    }


def _validate_platform_observation(value: Any, requested_selector: str, *, require_locations: bool = True, runtime_contract: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != set(evidence_contract.PLATFORM_KEYS):
        _fail("platform", "platform observation is not the closed evidence schema")
    if requested_selector not in evidence_contract.PLATFORM_SELECTORS or value.get("selector") != requested_selector:
        _fail("platform", "actual platform does not match the fixed selector")
    result = dict(value)
    for key, item in result.items():
        if key == "cpu_features":
            if not isinstance(item, list) or not item or len(item) > 128 or any(type(x) is not str or len(x.encode("utf-8")) > 256 for x in item):
                _fail("platform", "platform cpu_features are malformed")
        elif key not in {"locations", "runtime", "build_receipt"} and (type(item) is not str or len(item.encode("utf-8")) > 1024):
            _fail("platform", f"platform field {key} is malformed")
    # Reuse the evidence owner's closed nested schemas. This deliberately
    # rejects missing location/runtime/build facts rather than supporting from
    # a partial ambient probe.
    evidence_contract._platform(result, "exact-attempt platform", requested_selector)
    if runtime_contract is not None:
        runtime = result.get("runtime")
        if not isinstance(runtime, Mapping):
            _fail("platform", "Python runtime observation is missing")
        if not isinstance(runtime.get("implementation"), str) or runtime["implementation"].casefold() != str(runtime_contract["implementation"]).casefold():
            _fail("platform", "Python implementation differs from the bounded runtime contract")
        version = runtime.get("version")
        if type(version) is not str or version != runtime_contract["version"] or runtime.get("python_version") != runtime_contract["version"]:
            _fail("platform", "Python version differs from the bounded runtime contract")
    locations = result["locations"]
    for name in ("package", "output", "work"):
        if locations[name] is None:
            _fail("platform", f"required {name} location observation is missing")
    if require_locations and (locations["custody"] is None or any(locations["roles"].get(role) is None for role in ROLE_ORDER)):
        _fail("platform", "required custody/role location observation is missing")
    return result


def _frame_hash(frames: Sequence[bytes], domain: bytes) -> str:
    return evidence_contract._framed_hash(list(frames), domain)


def _hash_pair(frames: Sequence[bytes], domain: bytes) -> dict[str, Any]:
    return {"count": len(frames), "sha256": _frame_hash(frames, domain)}


def _fp_state(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if isinstance(value, Mapping):
        source = value
        fields = ("x87_control_word", "mxcsr", "x87_rounding_mode", "mxcsr_rounding_mode", "x87_exception_masks", "mxcsr_exception_masks", "x87_flags", "mxcsr_flags", "ftz", "daz")
        if not all(field in source for field in fields):
            return None
        output = {field: source[field] for field in fields}
    else:
        try:
            source = value.to_dict()
        except (AttributeError, TypeError):
            return None
        fields = ("x87_control_word", "mxcsr", "x87_rounding_mode", "mxcsr_rounding_mode", "x87_exception_masks", "mxcsr_exception_masks", "x87_flags", "mxcsr_flags", "ftz", "daz")
        if not all(field in source for field in fields):
            return None
        output = {field: source[field] for field in fields}
    # Contract FE register fields are lowercase fixed-width hex strings.
    for field, digits in (("x87_control_word", 4), ("mxcsr", 8)):
        number = output[field]
        if isinstance(number, int):
            output[field] = f"0x{number:0{digits}x}"
    return output


def _valid_fp_state(value: Any) -> dict[str, Any] | None:
    try:
        state = _fp_state(value)
        if state is None:
            return None
        evidence_contract._fe_state(state, "exact-attempt FP observation")
        return state
    except Exception:
        return None


def _valid_sha(value: Any) -> str | None:
    if type(value) is not str or len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        return None
    return value


def _bounded_detail(value: Any, fallback: str, maximum: int = 1024) -> str:
    if type(value) is not str:
        return fallback
    return value.replace("\x00", "?").replace("\r", " ").replace("\n", " ")[:maximum]


def _valid_lifecycle(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, Mapping) or set(value) != {"state", "exit_code", "term_signal", "reaped", "killed", "partial", "clean_shutdown", "startup_error", "rusage"}:
        return None
    state = value.get("state")
    exit_code = value.get("exit_code")
    if state not in {"exited", "terminated", "failed"} or type(exit_code) is not int or not -128 <= exit_code <= 255:
        return None
    term_signal = value.get("term_signal")
    if term_signal is not None and (type(term_signal) is not int or not 1 <= term_signal <= 64):
        return None
    if any(type(value.get(key)) is not bool for key in ("reaped", "killed", "partial", "clean_shutdown")):
        return None
    startup_error = value.get("startup_error")
    if type(startup_error) is not str or len(startup_error.encode("utf-8")) > 4096:
        return None
    usage = value.get("rusage")
    if usage is not None:
        if not isinstance(usage, Mapping) or set(usage) != {"user_seconds", "system_seconds", "max_rss", "minor_faults", "major_faults", "involuntary_context_switches", "voluntary_context_switches"}:
            return None
        if any(type(item) not in (int, float) or isinstance(item, bool) or item < 0 or not math.isfinite(float(item)) for item in usage.values()):
            return None
        usage = dict(usage)
    if state == "terminated" and term_signal is None and exit_code >= 0:
        return None
    return {"state": state, "exit_code": exit_code, "term_signal": term_signal, "reaped": value["reaped"], "killed": value["killed"], "partial": value["partial"], "clean_shutdown": value["clean_shutdown"], "startup_error": startup_error, "rusage": usage}


def _valid_output(value: Any) -> tuple[dict[str, Any] | None, bool]:
    if not isinstance(value, Mapping):
        return None, value is not None
    output: dict[str, Any] = {}
    malformed = False
    for key in ("missing", "extra", "trailing"):
        items = value.get(key, [])
        if not isinstance(items, (list, tuple)):
            malformed = True
            output[key] = []
            continue
        retained: list[str] = []
        for item in items:
            if type(item) is str:
                try:
                    if item and len(item.encode("utf-8")) <= MAX_OUTPUT_ID_BYTES:
                        retained.append(item)
                        continue
                except UnicodeEncodeError:
                    pass
            malformed = True
            retained.append(MALFORMED_OUTPUT_ID)
        output[key] = list(dict.fromkeys(retained))[:MAX_OUTPUT_IDS]
    for key, maximum in (("stdout", transport.STDOUT_TOTAL_CAP), ("stderr", transport.STDERR_TOTAL_CAP)):
        if key not in value:
            output[key] = None
            continue
        stream = value.get(key)
        if stream is None:
            output[key] = None
            continue
        if not isinstance(stream, Mapping) or set(stream) != {"bytes", "sha256"}:
            malformed = True
            output[key] = None
            continue
        size = stream.get("bytes")
        digest = _valid_sha(stream.get("sha256"))
        if type(size) is not int or size < 0 or size > maximum or digest is None:
            malformed = True
            output[key] = None
        else:
            output[key] = {"bytes": size, "sha256": digest}
    return output, malformed


EXECUTION_IDENTITY_KEYS = (
    "descriptor_pre", "descriptor_post_exe", "descriptor_post_fd",
    "cwd_pre", "cwd_post", "cwd_terminal", "content_initial", "content_pre_fork",
    "content_post_exec", "seals_initial", "seals_pre_fork", "seals_post_exec",
)


def _identity_mapping(value: Any, *, content: bool = False) -> dict[str, Any] | None:
    if value is None:
        return None
    if hasattr(value, "to_dict"):
        try:
            value = value.to_dict()
        except Exception:
            return None
    if not isinstance(value, Mapping):
        return None
    if content:
        digest = _valid_sha(value.get("sha256"))
        size = value.get("size")
        if digest is None or type(size) is not int or size < 0:
            return None
        return {"size": size, "sha256": digest}
    expected = {"device", "inode", "mode", "size", "nlink"}
    if set(value) != expected or any(type(value[key]) is not int or value[key] < 0 for key in expected):
        return None
    return {key: int(value[key]) for key in ("device", "inode", "mode", "size", "nlink")}


def _execution_identity(launch: Any, prepared_cwd: Mapping[str, int] | None, result: Any = None) -> tuple[dict[str, Any] | None, list[str]]:
    if launch is None:
        return None, []
    launch_dict: Mapping[str, Any] | None = None
    try:
        candidate = launch.to_dict() if hasattr(launch, "to_dict") else launch
        if isinstance(candidate, Mapping):
            launch_dict = candidate
    except Exception:
        return None, ["invalid-execution-identity"]
    if launch_dict is None:
        return None, ["invalid-execution-identity"]
    identity: dict[str, Any] = {}
    issues: list[str] = []
    for key in EXECUTION_IDENTITY_KEYS:
        raw = launch_dict.get(key)
        if key == "cwd_terminal" and raw is None:
            raw = _get(result, "terminal_cwd", None)
        if key.startswith("descriptor_") or key.startswith("cwd_"):
            value = _identity_mapping(raw)
        elif key.startswith("content_"):
            value = _identity_mapping(raw, content=True)
        else:
            value = raw if raw is None or (type(raw) is int and raw >= 0) else None
        if raw is not None and value is None:
            issues.append(f"invalid-{key}")
        elif key == "cwd_terminal" and value is None:
            issues.append("missing-cwd-terminal")
        identity[key] = value
    for key in ("cwd_pre", "cwd_post", "cwd_terminal"):
        observed = identity[key]
        if prepared_cwd is not None and observed is None:
            issues.append(f"missing-{key}")
        if observed is not None and prepared_cwd is not None and observed != dict(prepared_cwd):
            issues.append(f"{key}-mismatch")
    # A transport LaunchResult can legitimately retain a descriptor-shaped
    # object whose entire identity chain is null after a pre-exec failure.
    # The evidence contract represents that as absent incomplete evidence;
    # retaining an all-null object would be rejected as a partial identity
    # containing no observed field.
    if all(value is None for value in identity.values()):
        return None, issues
    return identity, issues


def _get(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def _transport_result(session: Any, result: Any) -> Any:
    """Return only an actual transport result, never configured cohort data."""
    del session
    return result


def _observed_content_hashes(identity: Mapping[str, Any] | None, launch: Any = None, result: Any = None) -> dict[str, str]:
    """Extract independently valid content hashes, even from partial metadata."""
    observed: dict[str, str] = {}
    for key in ("content_initial", "content_pre_fork", "content_post_exec"):
        content = identity.get(key) if identity is not None else None
        digest = _valid_sha(content.get("sha256")) if isinstance(content, Mapping) else None
        if digest is None:
            raw = _get(launch, key, None)
            if raw is None and key == "content_post_exec":
                raw = _get(result, key, None)
            digest = _valid_sha(_get(raw, "sha256", None))
        if digest is not None:
            observed[key] = digest
    return observed


def _content_custody_issues(identity: Mapping[str, Any] | None, candidate_sha256: str, launch: Any = None, result: Any = None) -> list[str]:
    """Retain and independently check every observed executable content hash."""
    return [
        f"{key}-custody-mismatch"
        for key, digest in _observed_content_hashes(identity, launch, result).items()
        if digest != candidate_sha256
    ]


def _candidate_binary_from_identity(identity: Mapping[str, Any] | None, launch: Any = None, result: Any = None) -> dict[str, str] | None:
    """Build the two-sided candidate identity only from observed content."""
    observed = _observed_content_hashes(identity, launch, result)
    pre_hash = observed.get("content_initial") or observed.get("content_pre_fork")
    post_hash = observed.get("content_post_exec")
    if pre_hash is not None and post_hash is not None:
        return {"sha256_pre": pre_hash, "sha256_post": post_hash}
    return None


def _session_is_closed(session: Any) -> bool:
    """Trust only an explicit boolean closed marker before skipping close()."""
    for name in ("_closed", "closed"):
        try:
            value = getattr(session, name)
        except Exception:
            continue
        if type(value) is bool:
            if value:
                return True
    return False


def _actual_bytes(result: Any, field: str) -> tuple[tuple[bytes, ...] | None, bool]:
    """Read a bounded transport prefix and report malformed field shape."""
    value = _get(result, field, None)
    if value is None:
        return None, False
    if isinstance(value, (bytes, bytearray, str)):
        return None, True
    try:
        values = tuple(value)
    except (TypeError, ValueError, RuntimeError):
        return None, True
    if len(values) > MAX_OUTPUT_IDS:
        return None, True
    if any(type(item) is not bytes or not item or len(item) > transport.FRAME_BYTES for item in values):
        return None, True
    return values, False


def _frame_request_id(raw: bytes) -> str | None:
    try:
        value = adjudicator.parse_json(raw, label="transport request")
    except Exception:
        return None
    return value.get("request_id") if isinstance(value, Mapping) and type(value.get("request_id")) is str else None


def _frame_response_id(raw: bytes) -> str | None:
    try:
        value = adjudicator.parse_json(raw, label="transport response")
    except Exception:
        return None
    return value.get("request_id") if isinstance(value, Mapping) and type(value.get("request_id")) is str else None


def _safe_output_id(value: Any, fallback: str) -> str:
    if type(value) is str:
        try:
            if value and len(value.encode("utf-8")) <= MAX_OUTPUT_ID_BYTES:
                return value
        except UnicodeEncodeError:
            pass
    return fallback


def _transport_prefix(
    expected_requests: Sequence[bytes], expected_ids: Sequence[str], result: Any,
) -> tuple[dict[str, Any], list[tuple[str, bytes]], str, str]:
    """Correlate actual request/response prefixes without inventing bytes.

    ``requests`` is the transport's admitted/write-attempted prefix.  It is
    never replaced with the configured cohort.  Only response frames that are
    strictly correlated and validator-approved are sent to adjudication.
    """
    if result is None:
        return {"requests": None, "responses": None, "missing": list(expected_ids[:MAX_OUTPUT_IDS]), "extra": [], "trailing": []}, [], "inconclusive", "transport result unavailable"
    actual_requests, malformed_requests = _actual_bytes(result, "requests")
    actual_responses, malformed_responses = _actual_bytes(result, "responses")
    markers = {"missing": [], "extra": [], "trailing": []}
    if malformed_requests:
        markers["extra"].append(MALFORMED_OUTPUT_ID)
    if malformed_responses:
        markers["extra"].append(MALFORMED_OUTPUT_ID)
    admitted: tuple[bytes, ...] = ()
    if actual_requests is not None:
        prefix: list[bytes] = []
        for index, raw in enumerate(actual_requests):
            actual_id = _frame_request_id(raw)
            id_matches = actual_id is None or (index < len(expected_ids) and actual_id == expected_ids[index])
            if index < len(expected_requests) and raw == expected_requests[index] and id_matches:
                prefix.append(raw)
            else:
                markers["extra"].append(_safe_output_id(actual_id, MISMATCH_OUTPUT_ID if actual_id is not None else EXTRA_OUTPUT_ID))
                break
        admitted = tuple(prefix)
        if len(actual_requests) < len(expected_requests):
            markers["missing"].extend(expected_ids[len(actual_requests):])
    response_prefix: list[bytes] = []
    pairs: list[tuple[str, bytes]] = []
    expected_prefix_ids = list(expected_ids[:len(admitted)])
    seen: set[str] = set()
    if actual_responses is None:
        if actual_requests is not None:
            markers["missing"].extend(expected_prefix_ids)
    else:
        for index, raw in enumerate(actual_responses):
            request_id = _frame_response_id(raw)
            if request_id is None:
                markers["extra"].append(MALFORMED_OUTPUT_ID)
                break
            if request_id in seen:
                markers["extra"].append(_safe_output_id(request_id, EXTRA_OUTPUT_ID))
                break
            seen.add(request_id)
            if index >= len(expected_prefix_ids):
                markers["extra"].append(_safe_output_id(request_id, EXTRA_OUTPUT_ID))
                break
            expected_id = expected_prefix_ids[index]
            if request_id != expected_id:
                markers["extra"].append(_safe_output_id(request_id, MISMATCH_OUTPUT_ID))
                break
            try:
                adjudicator.validate_response_frame(raw, expected_id)
            except Exception:
                markers["extra"].append(_safe_output_id(request_id, MALFORMED_OUTPUT_ID))
                break
            response_prefix.append(raw)
            pairs.append((expected_id, raw))
        if len(response_prefix) < len(expected_prefix_ids):
            markers["missing"].extend(expected_prefix_ids[len(response_prefix):])
    if _get(result, "trailing_stdout", b""):
        markers["trailing"].append(TRAILING_OUTPUT_ID)
    for key in markers:
        markers[key] = list(dict.fromkeys(markers[key]))[:MAX_OUTPUT_IDS]
    request_pair = None if actual_requests is None or malformed_requests else _hash_pair(admitted, evidence_contract.REQUEST_FRAME_DOMAIN)
    response_pair = None if actual_responses is None or malformed_responses else _hash_pair(response_prefix, evidence_contract.RESPONSE_FRAME_DOMAIN)
    status = str(_get(result, "status", "inconclusive"))
    detail = str(_get(result, "detail", "") or "")[:512]
    if markers["extra"] or markers["trailing"]:
        status = "failed"
        detail = detail or "transport response/output was malformed, mismatched, or extra"
    elif markers["missing"]:
        status = "inconclusive" if status == "supported" else status
        detail = detail or "transport response prefix is incomplete"
    return {"requests": request_pair, "responses": response_pair, **markers}, pairs, status, detail


def _process_observation(
    role: str,
    role_dir: Path,
    requests: Sequence[bytes],
    request_ids: Sequence[str],
    session: Any,
    result: Any,
    platform_value: Mapping[str, Any],
    candidate_sha256: str,
    prepared_cwd_identity: Mapping[str, int] | None,
) -> dict[str, Any]:
    result = _transport_result(session, result)
    issues: list[str] = []
    try:
        transport_view, _, status, transport_detail = _transport_prefix(requests, request_ids, result)
    except Exception:
        transport_view = {"requests": None, "responses": None, "missing": list(request_ids[:MAX_OUTPUT_IDS]), "extra": [MALFORMED_OUTPUT_ID], "trailing": []}
        status, transport_detail = "failed", "transport observation normalization failed"
        issues.append("transport-normalization-failed")
    if status not in {"supported", "failed", "inconclusive"}:
        status = "inconclusive"
        issues.append("invalid-status")
    raw_code = _get(result, "code", None)
    code = _bounded_detail(raw_code, "", 256) if type(raw_code) is str and raw_code else None
    if raw_code is not None and code is None:
        issues.append("invalid-code")
    detail = _bounded_detail(_get(result, "detail", None), transport_detail or "candidate transport did not provide a complete observation")

    launch = _get(result, "launch", None)
    launch_observed = launch is not None
    launch_dict: Mapping[str, Any] | None = None
    if launch_observed:
        try:
            candidate_launch = _get(launch, "to_dict", lambda: launch)()
            if isinstance(candidate_launch, Mapping):
                launch_dict = candidate_launch
            else:
                issues.append("invalid-launch-metadata")
        except Exception:
            issues.append("invalid-launch-metadata")
    launch_identity = f"exact-{role}"
    if launch_dict is not None:
        launch_identity = _bounded_detail(launch_dict.get("identity"), launch_identity, 1024)
    execution_identity, identity_issues = _execution_identity(launch, prepared_cwd_identity, result)
    issues.extend(identity_issues)
    issues.extend(_content_custody_issues(execution_identity, candidate_sha256, launch, result))

    candidate_binary: dict[str, Any] | None = None
    binary_source = _get(result, "candidate_binary", None)
    if binary_source is not None:
        pre_hash = _valid_sha(_get(binary_source, "sha256_pre", None))
        post_hash = _valid_sha(_get(binary_source, "sha256_post", None))
        if pre_hash is not None and post_hash is not None:
            candidate_binary = {"sha256_pre": pre_hash, "sha256_post": post_hash}
        else:
            issues.append("invalid-binary-metadata")
    if candidate_binary is None and launch_observed:
        observed_content = _observed_content_hashes(execution_identity, launch, result)
        candidate_binary = _candidate_binary_from_identity(execution_identity, launch, result)
        pre_observed = any(key in observed_content for key in ("content_initial", "content_pre_fork"))
        post_observed = "content_post_exec" in observed_content
        if pre_observed and not post_observed:
            issues.append("candidate-binary-post-missing")
        elif post_observed and not pre_observed:
            issues.append("candidate-binary-pre-missing")
    if candidate_binary is not None and (candidate_binary["sha256_pre"] != candidate_sha256 or candidate_binary["sha256_post"] != candidate_sha256):
        issues.append("candidate-binary-custody-mismatch")

    lifecycle_raw = _get(result, "lifecycle", None)
    lifecycle = _valid_lifecycle(lifecycle_raw)
    if lifecycle_raw is not None and lifecycle is None:
        issues.append("invalid-lifecycle")
    if lifecycle is None:
        returncode = _get(result, "returncode", None)
        if type(returncode) is int and not isinstance(returncode, bool) and -128 <= returncode <= 255:
            lifecycle = {
                "state": "exited" if returncode >= 0 else "terminated", "exit_code": returncode,
                "term_signal": _get(result, "term_signal", None), "reaped": _get(result, "reaped", False) is True,
                "killed": _get(result, "killed", False) is True, "partial": _get(result, "partial", False) is True,
                "clean_shutdown": _get(result, "clean_shutdown", False) is True,
                "startup_error": _bounded_detail(_get(result, "startup_error", b"").decode("utf-8", errors="replace") if isinstance(_get(result, "startup_error", b""), bytes) else _get(result, "startup_error", ""), "", 4096),
                "rusage": _get(result, "rusage", None),
            }

    output, output_malformed = _valid_output(_get(result, "output", None))
    if result is not None and output is None:
        output = {"missing": [], "extra": [], "trailing": [], "stdout": None, "stderr": None}
    if output_malformed:
        issues.append("invalid-output-metadata")
        if output is not None:
            output["extra"].append(MALFORMED_OUTPUT_ID)
    if output is not None:
        for key in ("missing", "extra", "trailing"):
            output[key].extend(transport_view[key])
            output[key] = list(dict.fromkeys(_safe_output_id(item, MALFORMED_OUTPUT_ID) for item in output[key]))[:MAX_OUTPUT_IDS]

    fe: dict[str, Any] | None = None
    fe_raw = _get(result, "fe_mxcsr", None)
    if fe_raw is not None and isinstance(fe_raw, Mapping):
        pre = _valid_fp_state(fe_raw.get("pre"))
        post = _valid_fp_state(fe_raw.get("post"))
        if pre is not None and post is not None:
            fe = {"pre": pre, "post": post}
        else:
            issues.append("invalid-fe-metadata")
    elif fe_raw is not None:
        issues.append("invalid-fe-metadata")
    if fe is None:
        pre = _valid_fp_state(_get(launch, "observation", None))
        post = _valid_fp_state(_get(result, "final_observation", None))
        if pre is not None and post is not None:
            fe = {"pre": pre, "post": post}
        elif pre is not None:
            issues.append("fe-pre-observed-final-missing")
    if issues:
        detail = _bounded_detail(detail + "; " + "; ".join(issues), "candidate process observation is incomplete")
        failure_issues = [item for item in issues if item not in {"fe-pre-observed-final-missing", "candidate-binary-post-missing", "candidate-binary-pre-missing", "missing-cwd-terminal", "missing-cwd_terminal", "invalid-lifecycle"}]
        if status == "supported" or failure_issues:
            status = "failed"
    if code is None and status != "supported":
        code = "observation-incomplete"
    complete = (
        launch_observed and candidate_binary is not None and fe is not None and lifecycle is not None and output is not None
        and execution_identity is not None and not identity_issues
        and transport_view["requests"] is not None and transport_view["responses"] is not None
        and transport_view["requests"]["count"] == len(requests) and transport_view["responses"]["count"] == len(requests)
        and not any(output[key] for key in ("missing", "extra", "trailing"))
        and output.get("stdout") is not None and output.get("stderr") is not None
    )
    if not complete:
        if status == "supported":
            status = "inconclusive"
            code = code or "observation-incomplete"
            detail = _bounded_detail(detail + "; observation-incomplete", "candidate process observation is incomplete")
        return _incomplete_process(role, len(requests), transport_view, platform_value, launch_observed, launch_identity, str(role_dir), candidate_binary, fe, lifecycle, output, execution_identity, status, code, detail)
    launch_output = {
        "identity": launch_identity,
        "argv": [CANDIDATE_ARGV0],
        "cwd": str(role_dir),
        "environment": dict(CANDIDATE_ENVIRONMENT),
    }
    process = {
        "variant": "complete-v1",
        "role": role,
        "candidate_request_count": len(requests),
        "platform": dict(platform_value),
        "launch": launch_output,
        "candidate_binary": candidate_binary,
        "execution_identity": execution_identity,
        "fe_mxcsr": fe,
        "transport": {"requests": transport_view["requests"], "responses": transport_view["responses"]},
        "lifecycle": dict(lifecycle),
        "output": {
            **{key: list(output.get(key, [])) for key in ("missing", "extra", "trailing")},
            "stdout": dict(output["stdout"]), "stderr": dict(output["stderr"]),
        },
        "outcome": {"status": status, "code": None if status == "supported" else str(code), "detail": None if status == "supported" else str(detail)},
    }
    return process


def _incomplete_process(role: str, count: int, transport_view: Mapping[str, Any], platform_value: Mapping[str, Any] | None, launch_observed: bool, launch_identity: str, role_dir: str, binary: Mapping[str, Any] | None, fe: Any, lifecycle: Mapping[str, Any] | None, output: Mapping[str, Any] | None, execution_identity: Mapping[str, Any] | None, status: str, code: Any, detail: Any) -> dict[str, Any]:
    outcome_status = status if status in {"supported", "failed", "inconclusive"} else "inconclusive"
    if outcome_status == "supported":
        outcome_status = "inconclusive"
    retained = {
        "variant": "incomplete-v1",
        "role": role,
        "candidate_request_count": count,
        "platform": None if platform_value is None else dict(platform_value),
        "launch": None if not launch_observed else {"identity": launch_identity, "argv": [CANDIDATE_ARGV0], "cwd": role_dir, "environment": dict(CANDIDATE_ENVIRONMENT)},
        "candidate_binary": None if binary is None else dict(binary),
        "execution_identity": None if execution_identity is None else dict(execution_identity),
        "fe_mxcsr": None if fe is None else fe,
        "transport": {"requests": transport_view.get("requests"), "responses": transport_view.get("responses")},
        "lifecycle": None if lifecycle is None else dict(lifecycle),
        "output": None if output is None else {
            **{key: list(output.get(key, [])) for key in ("missing", "extra", "trailing")},
            "stdout": None if output.get("stdout") is None else dict(output["stdout"]),
            "stderr": None if output.get("stderr") is None else dict(output["stderr"]),
        },
        "outcome": {"status": outcome_status, "code": None if outcome_status == "supported" else str(code or "transport-incomplete"), "detail": None if outcome_status == "supported" else str(detail or "candidate process observation is incomplete")},
    }
    missing = []
    for key in ("platform", "launch", "candidate_binary", "execution_identity", "fe_mxcsr", "lifecycle", "output"):
        if retained[key] is None:
            missing.append(key)
    for key in ("requests", "responses"):
        if retained["transport"][key] is None:
            missing.append(f"transport.{key}")
    if retained["execution_identity"] is not None and retained["execution_identity"].get("cwd_terminal") is None:
        missing.append("execution_identity.cwd_terminal")
    if retained["output"] is not None:
        for key in ("stdout", "stderr"):
            if retained["output"].get(key) is None:
                missing.append(f"output.{key}")
    retained["missing"] = missing
    return retained


@dataclass(frozen=True)
class _ExactAttemptDependencies:
    """Private dependency bundle used only by the focused synthetic tests."""

    preflight: Callable[..., Any] = gate_b_preflight.build_gate_b_preflight
    prepare: Callable[..., Any] = adjudicator.prepare_exact_attempt
    validate_admission: Callable[..., Any] = authority.validate_gate_b_admission
    validate_authorization: Callable[..., Any] = authority.validate_authorization
    validate_custody_record: Callable[..., Any] = custody.validate_custody_record
    verify_custody: Callable[..., Any] = custody.verify_and_materialize
    reserve_attempt: Callable[..., Any] = publication.reserve_experiment_slot
    transport_factory: Callable[..., Any] = transport.ExactCandidateSession
    adjudicate: Callable[..., Any] = adjudicator.adjudicate_exact
    build_result: Callable[..., bytes] = evidence_contract.build_result
    build_receipt: Callable[..., bytes] = evidence_contract.build_receipt
    build_attempt_index: Callable[..., bytes] = evidence_contract.build_attempt_index
    publish_reserved_attempt: Callable[..., Any] = publication.publish_reserved_attempt
    platform_probe: Callable[[str], Mapping[str, Any]] = _platform_observation
    validate_exact_tools: Callable[..., Any] | None = None


@dataclass(frozen=True)
class ExactAttemptRun:
    """All in-memory outputs from one published exact attempt."""

    attempt_id: str
    prepared: Any
    adjudication: Any
    process_observations: tuple[Mapping[str, Any], ...]
    result_bytes: bytes
    receipt_bytes: bytes
    index_bytes: bytes
    published: Any
    reservation_record: bytes | None = None


def _validate_exact_tool_closure(validator: Callable[..., Any], freeze: Mapping[str, Any]) -> Any:
    """Call either generation of the authority validator without hiding errors."""
    try:
        parameters = inspect.signature(validator).parameters
    except (TypeError, ValueError):
        parameters = {}
    if "require_complete" in parameters:
        return validator(freeze, require_complete=True)
    return validator(freeze)


def _validate_prepared_cohorts(prepared: Any) -> tuple[Any, ...]:
    cohorts = tuple(getattr(prepared, "transport", ()))
    if len(cohorts) != len(ROLE_ORDER) or [getattr(item, "role", None) for item in cohorts] != list(ROLE_ORDER):
        _fail("cohort", "prepared transport cohorts are not in the fixed role order")
    for cohort in cohorts:
        role = getattr(cohort, "role", None)
        if role not in ROLE_REQUEST_COUNTS:
            _fail("cohort", "prepared transport cohort has an unknown role")
        requests = tuple(getattr(cohort, "request_bytes", ()))
        request_ids = tuple(getattr(cohort, "request_ids", ()))
        if len(requests) != ROLE_REQUEST_COUNTS[role] or len(request_ids) != len(requests):
            _fail("cohort", "prepared transport cohort count differs from 8/40/9")
        if any(type(raw) is not bytes or not raw for raw in requests) or any(type(item) is not str or not item for item in request_ids):
            _fail("cohort", "prepared transport cohort contains malformed request data")
    return cohorts


def _validate_reservation(
    value: Any,
    successor_manifest_sha256: str,
    platform_selector: str,
    ordinal: int,
    attempt_id: str,
) -> Any:
    """Require a live handle bound to this exact experiment slot."""
    close = getattr(value, "close", None) if value is not None else None
    try:
        value_attempt_id = getattr(value, "attempt_id")
        closed = getattr(value, "closed")
        experiment_slot = getattr(value, "experiment_slot")
    except Exception as error:
        if callable(close):
            try:
                close()
            except Exception:
                pass
        raise ExactAttemptError("reservation", "reserve_experiment_slot returned a malformed handle") from error
    expected_slot = {
        "successor_manifest_sha256": successor_manifest_sha256,
        "platform_selector": platform_selector,
        "ordinal": ordinal,
        "attempt_id": attempt_id,
    }
    try:
        slot_matches = isinstance(experiment_slot, Mapping) and dict(experiment_slot) == expected_slot
    except (TypeError, ValueError):
        slot_matches = False
    valid = type(value_attempt_id) is str and callable(close) and type(closed) is bool and slot_matches
    if not valid or value_attempt_id != attempt_id or closed is not False:
        if callable(close) and closed is False:
            try:
                close()
            except Exception:
                pass
        _fail("reservation", "reserve_experiment_slot did not return a live handle bound to the requested slot")
    return value


def _retain_terminal_failure(reservation: Any, error: BaseException) -> None:
    """Best-effort terminal evidence for a real consumed reservation.

    Synthetic dependency reservations intentionally do not own filesystem
    evidence.  The production publication reservation does, and its terminal
    writer preserves the consumed slot before the outer cleanup closes it.
    """
    if not isinstance(reservation, publication.AttemptReservation):
        return
    if getattr(reservation, "closed", True):
        return
    try:
        publication.write_terminal_failure(
            reservation,
            code=getattr(error, "code", "attempt-failure"),
            detail=str(error)[:1024] or "exact attempt failed after reservation",
            status="failed",
        )
    except Exception:
        # The original failure remains authoritative; closure marks the
        # consumed slot inconclusive if no terminal record was retained.
        return


def _run_exact_attempt_with_dependencies(
    package_root: str | Path,
    attempt_id: str,
    *,
    platform_selector: str,
    ordinal: int,
    freeze_manifest: bytes,
    admission_record: bytes,
    authorization_record: bytes,
    custody_record: bytes,
    review_root: str | Path,
    candidate_identity: Mapping[str, Any],
    tool_identities: Sequence[Mapping[str, Any]],
    output_root: str | Path,
    work_root: str | Path,
    dependencies: _ExactAttemptDependencies | None = None,
) -> ExactAttemptRun:
    """Validate and execute exactly one fixed Phase 3 attempt.

    The function has no candidate-path, argv, environment, retry, or process
    count parameters.  A failure after reservation is raised only after the
    reservation has been closed; the durable marker is intentionally left in
    place by the publication module.
    """
    if dependencies is None:
        deps = _ExactAttemptDependencies()
    elif isinstance(dependencies, _ExactAttemptDependencies):
        deps = dependencies
    elif isinstance(dependencies, Mapping):
        try:
            deps = _ExactAttemptDependencies(**dict(dependencies))
        except (TypeError, ValueError) as error:
            raise ExactAttemptError("dependencies", "dependency mapping is not a closed boundary set") from error
    else:
        raise ExactAttemptError("dependencies", "private test dependencies must be _ExactAttemptDependencies or a mapping")
    attempt_id = _attempt_id(attempt_id)
    if platform_selector not in PLATFORM_ORDINALS or type(ordinal) is not int or ordinal not in PLATFORM_ORDINALS[platform_selector]:
        _fail("platform", "platform selector/ordinal is not preregistered")
    freeze_bytes = _bounded_bytes(freeze_manifest, "freeze manifest")
    admission_bytes = _bounded_bytes(admission_record, "admission record")
    authorization_bytes = _bounded_bytes(authorization_record, "authorization record")
    custody_bytes = _bounded_bytes(custody_record, "custody record")
    freeze, freeze_hash = _freeze_identity(freeze_bytes)
    admission_hash = _record_hash(admission_bytes, "admission record")
    authorization_hash = _record_hash(authorization_bytes, "authorization record")
    _record_hash(custody_bytes, "custody record")
    tools = _normalize_tools(tool_identities)
    evidence_tools = _validate_tool_binding(freeze, tools)
    package_path = _root_path(package_root, "package root")
    output_path = _root_path(output_root, "output root")
    work_path = _root_path(work_root, "work root")
    review_path = _root_path(review_root, "review root")
    # Only safe base roots are materialized before the static Gate-B checks.
    # Attempt-specific directories are created after the durable reservation.
    _ensure_directory(output_path, "output root")
    _ensure_directory(work_path, "work root")

    # Every call through these boundaries is read-only/non-executing until
    # reserve_attempt returns.  The explicit freeze bytes are retained rather
    # than reserialized or replaced by a path-selected manifest.
    verified = None
    runtime_contract: Mapping[str, Any] | None = None
    try:
        preflight_report = deps.preflight(package_path, candidate_identity, tools)
        if not isinstance(preflight_report, Mapping) or preflight_report.get("execution_permitted") is not False:
            _fail("preflight", "Gate B preflight did not return an execution-disabled report")
        execution_package = preflight_report.get("execution_package")
        if not isinstance(execution_package, Mapping) or execution_package.get("manifest_sha256") != freeze_hash:
            _fail("preflight", "Gate B preflight package does not bind the supplied freeze")
        if preflight_report.get("schema") != gate_b_preflight.SCHEMA:
            _fail("preflight", "Gate B preflight report is not the current schema")
        reported_tools = preflight_report.get("tool_identities")
        if reported_tools is None or _normalize_report_tools(reported_tools, "tool_identities") != tools:
            _fail("preflight", "Gate B preflight report does not retain the full frozen tool closure")
        for field in ("runtime_tool_identities", "exact_runtime_tool_identities", "provenance_tool_identities"):
            reported = execution_package.get(field)
            if reported is None or _normalize_report_tools(reported, f"execution_package.{field}") != _freeze_tool_collection(freeze, field):
                _fail("preflight", f"Gate B preflight {field} differs from the supplied freeze")
        _validate_source_snapshot_attestation(freeze, execution_package, tools)
        required_tool_validator = deps.validate_exact_tools or getattr(authority, "validate_required_exact_runtime_tools", None)
        if callable(required_tool_validator):
            _validate_exact_tool_closure(required_tool_validator, freeze)
        if deps.platform_probe is _platform_observation:
            runtime_contract = _validate_frozen_runtime_contract(freeze, platform_selector)
        admission_value = deps.validate_admission(admission_bytes, freeze_manifest=freeze_bytes, review_root=review_path)
        if not isinstance(admission_value, Mapping) or admission_value.get("freeze_manifest_sha256") != freeze_hash or admission_value.get("execution_permitted") is not False:
            _fail("admission", "Gate B admission validator returned a partial or execution-enabled record")
        custody_value = _canonical_record(custody_bytes, "custody record")
        static_custody = deps.validate_custody_record(
            custody_bytes,
            expected_manifest=freeze_bytes,
            expected_manifest_sha256=freeze_hash,
        )
        if not isinstance(static_custody, Mapping):
            _fail("custody", "static custody validation returned a partial record")
        selected_binary = _validate_selected_binary_compatibility(freeze, platform_selector, static_custody)
        # Custody's authenticated identity is its domain-framed self-hash,
        # while the evidence contract binds the exact admission and
        # authorization bytes by their ordinary SHA-256 identities.
        expected_custody_hash = custody_value.get("custody_record_sha256")
        if type(expected_custody_hash) is not str or len(expected_custody_hash) != 64 or any(char not in "0123456789abcdef" for char in expected_custody_hash):
            _fail("custody", "custody record self-hash field is malformed")
        # The static validator returns its normalized validated projection;
        # its production shape intentionally omits the raw self-hash field.
        # The canonical bytes above supplied that authenticated field, and a
        # successful validator call is the authority that checked its
        # domain-framed self-hash.
        custody_hash = expected_custody_hash
        authorization_value = deps.validate_authorization(
            authorization_bytes,
            admission_bytes=admission_bytes,
            freeze_manifest=freeze_bytes,
            review_root=review_path,
            expected_custody_record_sha256=custody_hash,
            expected_attempt_id=attempt_id,
            expected_platform_selector=platform_selector,
            expected_ordinal=ordinal,
        )
        if not isinstance(authorization_value, Mapping) or authorization_value.get("attempt_id") != attempt_id or authorization_value.get("platform_selector") != platform_selector or authorization_value.get("ordinal") != ordinal or authorization_value.get("execution_permitted") is not True or authorization_value.get("automatic_retry") is not False:
            _fail("authorization", "authorization validator returned a partial or retry-enabled record")
        authorization_reference = authorization_value.get("authorization_reference")
        if type(authorization_reference) is not str or not authorization_reference or len(authorization_reference.encode("utf-8")) > 256:
            _fail("authorization", "validated authorization reference is missing or unbounded")
        prepared = deps.prepare(package_path, attempt_id)
        cohorts = _validate_prepared_cohorts(prepared)
    except ExactAttemptError:
        if verified is not None:
            try:
                verified.close()
            except Exception:
                pass
        raise
    except Exception as error:
        if verified is not None:
            try:
                verified.close()
            except Exception:
                pass
        raise ExactAttemptError(getattr(error, "code", "preflight"), str(error)) from error

    try:
        frozen_build = None
        if deps.platform_probe is _platform_observation:
            frozen_build = _load_frozen_build_facts(package_path, freeze, platform_selector)
        pre_platform = deps.platform_probe(
            platform_selector, package_root=package_path, output_root=output_path,
            work_root=work_path, frozen_build=frozen_build,
        )
        _validate_platform_observation(pre_platform, platform_selector, require_locations=False, runtime_contract=runtime_contract)
    except ExactAttemptError:
        if verified is not None:
            try:
                verified.close()
            except Exception:
                pass
        raise
    except Exception as error:
        raise ExactAttemptError(getattr(error, "code", "custody"), str(error)) from error

    try:
        reservation = _validate_reservation(
            deps.reserve_attempt(output_path, freeze_hash, platform_selector, ordinal, attempt_id),
            freeze_hash, platform_selector, ordinal, attempt_id,
        )
    except Exception as error:
        raise ExactAttemptError(getattr(error, "code", "reservation"), str(error)) from error

    responses: list[tuple[str, bytes]] = []
    process_observations: list[Mapping[str, Any]] = []
    seen_sessions: set[int] = set()
    role_fds: dict[str, int] = {}
    role_dirs: dict[str, Path] = {}
    role_identities: dict[str, dict[str, int]] = {}
    try:
        custody_path, role_dirs, role_fds, role_identities = _prepare_work_locations(output_path, work_path, attempt_id)
        platform_value = _validate_platform_observation(
            deps.platform_probe(
                platform_selector, package_root=package_path, output_root=output_path,
                work_root=work_path, custody_root=custody_path, role_dirs=role_dirs,
                frozen_build=frozen_build,
            ),
            platform_selector,
            runtime_contract=runtime_contract,
        )
        verified = deps.verify_custody(
            custody_bytes,
            expected_manifest=freeze_bytes,
            expected_manifest_sha256=freeze_hash,
            invocation_dir=custody_path,
        )
        candidate_fd = _get(verified, "candidate_fd", None)
        if not isinstance(candidate_fd, int) or candidate_fd < 0:
            _fail("custody", "verified custody did not supply an open candidate descriptor")
        candidate_bytes = _get(verified, "candidate_bytes", None)
        candidate_sha256 = _valid_sha(_get(verified, "candidate_sha256", None))
        if type(candidate_bytes) is not int or candidate_bytes <= 0 or candidate_bytes > MAX_EXECUTABLE_BYTES or candidate_sha256 is None:
            _fail("custody", "verified custody did not supply a bounded candidate identity")
        if candidate_bytes != selected_binary["bytes"] or candidate_sha256 != selected_binary["sha256"]:
            _fail("custody", "materialized candidate differs from selected frozen binary slot")
        candidate_content = _read_candidate_descriptor(candidate_fd, candidate_bytes, candidate_sha256)
        for cohort in cohorts:
            role = getattr(cohort, "role", None)
            requests = tuple(getattr(cohort, "request_bytes", ()))
            request_ids = tuple(getattr(cohort, "request_ids", ()))
            if role not in ROLE_ORDER or len(requests) != ROLE_REQUEST_COUNTS[role] or len(request_ids) != len(requests):
                _fail("cohort", "prepared transport cohorts do not match the fixed role accounting")
            session = None
            result = None
            try:
                cwd_fd = role_fds.pop(role)
                try:
                    session = deps.transport_factory(
                        executable_fd=candidate_fd,
                        argv0=CANDIDATE_ARGV0,
                        env=dict(CANDIDATE_ENVIRONMENT),
                        cwd=None,
                        cwd_fd=cwd_fd,
                        expected_bytes=candidate_content,
                        expected_sha256=candidate_sha256,
                        frames=requests,
                        expected_fp=EXPECTED_FP,
                        auto_launch=False,
                    )
                finally:
                    try:
                        os.close(cwd_fd)
                    except OSError:
                        pass
                close_method = getattr(session, "close", None) if session is not None else None
                if not callable(close_method):
                    _fail("transport", "transport factory did not return a session with callable close()")
                if id(session) in seen_sessions:
                    _fail("transport", "transport factory reused a candidate session")
                seen_sessions.add(id(session))
                run_method = getattr(session, "run", None)
                if not callable(run_method):
                    _fail("transport", "transport factory did not return a session with run()")
                result = run_method()
                result_for_observation = _transport_result(session, result)
                _, valid_pairs, _, _ = _transport_prefix(requests, request_ids, result_for_observation)
                responses.extend(valid_pairs)
                process_observations.append(_process_observation(role, role_dirs[role], requests, request_ids, session, result_for_observation, platform_value, candidate_sha256, role_identities[role]))
            except Exception as error:
                # ``run()`` can raise after transport has already collected a
                # terminal result (for example a malformed frame, output cap,
                # or child signal).  Close once here so that result's bounded
                # lifecycle and stream observations survive into durable
                # incomplete evidence instead of being discarded by the
                # exception path.
                if session is not None and result is None and not _session_is_closed(session):
                    close_on_failure = getattr(session, "close", None)
                    if callable(close_on_failure):
                        try:
                            result = close_on_failure()
                        except Exception:
                            result = None
                result_for_observation = _transport_result(session, result) if session is not None else None
                transport_view, valid_pairs, transport_status, transport_detail = _transport_prefix(requests, request_ids, result_for_observation)
                responses.extend(valid_pairs)
                launch_for_failure = _get(session, "launch_result", None) or _get(session, "launch", None)
                launch_observed = launch_for_failure is not None
                execution_identity, identity_issues = _execution_identity(
                    launch_for_failure, role_identities.get(role), result_for_observation,
                )
                content_issues = _content_custody_issues(execution_identity, candidate_sha256, launch_for_failure, result_for_observation)
                failure_binary = _candidate_binary_from_identity(execution_identity, launch_for_failure, result_for_observation)
                failure_status = transport_status if transport_status in {"failed", "inconclusive"} else "inconclusive"
                failure_detail = str(error)[:1024] or transport_detail
                if identity_issues or content_issues:
                    failure_status = "failed"
                    failure_detail = (failure_detail + "; " + "; ".join((*identity_issues, *content_issues)))[:1024]
                if failure_binary is not None and (failure_binary["sha256_pre"] != candidate_sha256 or failure_binary["sha256_post"] != candidate_sha256):
                    failure_status = "failed"
                    failure_detail = (failure_detail + "; candidate-binary-custody-mismatch")[:1024]
                lifecycle = _valid_lifecycle(_get(result_for_observation, "lifecycle", None))
                output, output_malformed = _valid_output(_get(result_for_observation, "output", None))
                if output_malformed:
                    failure_detail = (failure_detail + "; invalid-output-metadata")[:1024]
                if output is not None:
                    for marker in ("missing", "extra", "trailing"):
                        output[marker] = list(dict.fromkeys(output[marker] + transport_view[marker]))[:MAX_OUTPUT_IDS]
                process_observations.append(_incomplete_process(
                    role, len(requests), transport_view, platform_value, launch_observed, f"exact-{role}", str(role_dirs[role]),
                    failure_binary, None, lifecycle, output, execution_identity, failure_status,
                    getattr(error, "code", "transport-failure"), failure_detail,
                ))
                continue
            finally:
                if session is not None and not _session_is_closed(session):
                    close_method = getattr(session, "close", None)
                    if callable(close_method):
                        try:
                            close_method()
                        except Exception:
                            pass

        # The adjudicator owns all 60-case accounting and is deliberately
        # called once with incomplete evidence enabled.  No response/process
        # failure is converted into a successful result by this wrapper.
        adjudication_run = deps.adjudicate(prepared, responses, allow_incomplete=True)
        inputs = adjudication_run.evidence_contract_inputs()
        attempt_metadata = {
            "freeze_manifest_sha256": freeze_hash,
            "attempt_id": attempt_id,
            "platform_selector": platform_selector,
            "ordinal": ordinal,
            "authorization_reference": authorization_reference,
            "gate_b_admission_sha256": admission_hash,
            "authorization_record_sha256": authorization_hash,
            "custody_record_sha256": custody_hash,
        }
        result_bytes = deps.build_result(
            attempt_metadata,
            inputs["adjudications"],
            process_observations,
            evidence_tools,
        )
        receipt_bytes = deps.build_receipt(result_bytes)
        index_bytes = deps.build_attempt_index(result_bytes, receipt_bytes, attempt_metadata)
        published = deps.publish_reserved_attempt(reservation, result_bytes, receipt_bytes, index_bytes)
        return ExactAttemptRun(
            attempt_id, prepared, adjudication_run, tuple(process_observations),
            result_bytes, receipt_bytes, index_bytes, published,
            getattr(published, "reservation_record", None),
        )
    except ExactAttemptError as error:
        _retain_terminal_failure(reservation, error)
        raise
    except Exception as error:
        _retain_terminal_failure(reservation, error)
        raise ExactAttemptError(getattr(error, "code", "attempt"), str(error)) from error
    finally:
        # Publication consumes/closes the reservation.  On every earlier
        # failure, close only the handle; the marker is deliberately retained.
        for fd in role_fds.values():
            try:
                os.close(fd)
            except OSError:
                pass
        try:
            if not getattr(reservation, "closed", True):
                reservation.close()
        except Exception:
            pass
        try:
            verified.close()
        except Exception:
            pass


_PRODUCTION_DEPENDENCIES = _ExactAttemptDependencies()


def run_exact_attempt(
    package_root: str | Path,
    attempt_id: str,
    *,
    platform_selector: str,
    ordinal: int,
    freeze_manifest: bytes,
    admission_record: bytes,
    authorization_record: bytes,
    custody_record: bytes,
    review_root: str | Path,
    candidate_identity: Mapping[str, Any],
    tool_identities: Sequence[Mapping[str, Any]],
    output_root: str | Path,
    work_root: str | Path,
) -> ExactAttemptRun:
    """Run using the frozen production dependency closure only."""
    return _run_exact_attempt_with_dependencies(
        package_root, attempt_id, platform_selector=platform_selector, ordinal=ordinal,
        freeze_manifest=freeze_manifest,
        admission_record=admission_record, authorization_record=authorization_record,
        custody_record=custody_record, review_root=review_root, candidate_identity=candidate_identity,
        tool_identities=tool_identities, output_root=output_root, work_root=work_root,
        dependencies=_PRODUCTION_DEPENDENCIES,
    )


def _run_exact_attempt_for_tests(*args: Any, dependencies: _ExactAttemptDependencies, **kwargs: Any) -> ExactAttemptRun:
    """Private synthetic-test seam; never exported through execution aliases."""
    return _run_exact_attempt_with_dependencies(*args, dependencies=dependencies, **kwargs)


# Explicit aliases make the fixed entrypoint discoverable while ensuring every
# public name uses the same frozen production dependency object.
execute_exact_attempt = run_exact_attempt
orchestrate_exact_attempt = run_exact_attempt
run = run_exact_attempt
execute = run_exact_attempt
exact_attempt = run_exact_attempt


__all__ = [
    "PHASE_ID", "EXPERIMENT_ID", "CANDIDATE_PROFILE_ID", "ROLE_ORDER", "ROLE_CASE_COUNTS", "ROLE_REQUEST_COUNTS",
    "PLATFORM_ORDINALS", "TARGET", "CANDIDATE_ARGV0", "CANDIDATE_ENVIRONMENT", "EXPECTED_FP",
    "ExactAttemptError", "ExactAttemptRun", "run_exact_attempt",
    "execute_exact_attempt", "orchestrate_exact_attempt", "run", "execute", "exact_attempt",
]

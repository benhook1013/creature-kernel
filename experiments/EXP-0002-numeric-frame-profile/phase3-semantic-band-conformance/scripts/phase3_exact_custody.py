#!/usr/bin/env python3
"""Fail-closed custody verification for the Phase 3 build artifact.

This module is deliberately a consumer boundary.  It consumes an already
created custody record and an already created transfer; it never rebuilds,
downloads, retries, starts, or otherwise substitutes a candidate.  A custody
record describes declared custody and an execution-prohibited policy.  It is
not causal build attestation (the build receipt remains a separate
build-only observation).

The public entry point is :func:`verify_and_materialize`.  It validates the
record against a caller-supplied successor freeze manifest/hash, consumes the
exact transfer bytes, validates the five-member bundle closure, and writes two
exclusive regular files into an empty invocation directory.  It returns open
descriptors and identities suitable for a descriptor-bound launcher, but does
not launch anything.
"""

from __future__ import annotations

import datetime as _dt
import fcntl
import hashlib
import importlib.util
import io
import json
import os
import re
import stat
import sys
import tarfile
import tempfile
import types
import zipfile
from pathlib import Path
from typing import Any, Mapping


PHASE_ID = "exp-0002-phase3-semantic-band-conformance-001"
EXPERIMENT_ID = "EXP-0002"
CANDIDATE_PROFILE_ID = "ck.provisional-r3-authored-conflict.semantic-band-1"
SCHEMA = "ck.exp-0002.phase3.gate-b-exact-artifact-custody-1"
SELF_HASH_DOMAIN = b"ck.exp-0002.phase3.gate-b-exact-artifact-custody.v1\0"
WORKFLOW_PATH = ".github/workflows/phase3-gate-b-native-build.yml"
# Custody is a current-artifact consumer.  Keep v3 available for diagnostics
# and historical records, but only the runtime-attested v5 freeze can authorize a
# new exact custody record.
FREEZE_SCHEMA = "ck.exp-0002.phase3.freeze-manifest-5"
LEGACY_FREEZE_SCHEMA = "ck.exp-0002.phase3.freeze-manifest-3"
EXPERIMENT_CLOSURE_SCHEMA = "ck.exp-0002.phase3.experiment-closure-1"
EXPERIMENT_CLOSURE_TOOL = "scripts/phase3_experiment_closure.py"
REQUIRED_EXACT_RUNTIME_TOOLS = (
    "scripts/phase3_exact_adjudicator.py",
    "scripts/phase3_exact_authority.py",
    "scripts/phase3_exact_custody.py",
    "scripts/phase3_exact_fp_observer.py",
    "scripts/phase3_exact_publication.py",
    "scripts/phase3_exact_transport.py",
    "scripts/phase3_exact_attempt.py",
    "scripts/phase3_exact_attempt_launcher.py",
)
REQUIRED_RUNTIME_TOOLS = (
    "scripts/phase3_common.py", "scripts/phase3_oracle.py", "scripts/phase3_scorer.py",
    "scripts/phase3_runner.py", "scripts/phase3_receipt.py", "scripts/phase3_materialized_adapter.py",
    "scripts/phase3_evidence_contract.py", "scripts/phase3_gate_b_preflight.py",
)
REQUIRED_PROVENANCE_TOOLS = (
    "scripts/generate_phase3.py", "scripts/check_candidate_prebinding.py",
    "scripts/phase3_build_receipt.py", "scripts/phase3_freeze_manifest.py",
    "scripts/phase3_python_runtime_probe.py",
)
TARGET = "x86_64-unknown-linux-gnu"
PROFILE = "dev"
RECEIPT_SCHEMA = "ck.exp-0002.phase3.gate-b-build-receipt-1"
METADATA_SCHEMA = "ck.exp-0002.phase3.gate-b-build-metadata-1"
BUNDLE_MEMBERS = ("candidate", "build-receipt.json", "build-metadata.json", "cargo-metadata.json", "SHA256SUMS")
MANIFEST_MEMBERS = BUNDLE_MEMBERS[:-1]
PLATFORM_SELECTORS = {
    "wsl2-x86_64": "wsl",
    "ubuntu-24.04-x86_64": "native",
}
MAX_RECORD_BYTES = 64 * 1024
MAX_JSON_BYTES = 16 * 1024 * 1024
MAX_JSON_DEPTH = 32
MAX_ZIP_BYTES = 128 * 1024 * 1024
MAX_BUNDLE_BYTES = 128 * 1024 * 1024
MAX_MEMBER_BYTES = 112 * 1024 * 1024
MAX_BUNDLE_MEMBERS = 5
MAX_CANDIDATE_BYTES = 512 * 1024 * 1024
MAX_RECEIPT_BYTES = 128 * 1024
MAX_METADATA_BYTES = 4 * 1024 * 1024
MAX_CARGO_BYTES = 8 * 1024 * 1024
MAX_ZIP_RATIO = 200
MAX_TAR_TRAILING_BYTES = 12 * 1024
GITHUB_RETENTION_DAYS = 90
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$")


class CustodyError(ValueError):
    """Stable, typed fail-closed custody error."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = str(code)
        self.detail = str(detail).replace("\x00", "?").replace("\n", " ").replace("\r", " ")[:300]
        super().__init__(f"{self.code}: {self.detail}" if self.detail else self.code)


class MaterializedIdentity:
    def __init__(self, *, path: Path, fd: int, mode: int, bytes: int, sha256: str) -> None:
        self.path, self.fd, self.mode, self.bytes, self.sha256 = path, fd, mode, bytes, sha256

    def close(self) -> None:
        fd, self.fd = self.fd, -1
        if fd >= 0:
            try:
                os.close(fd)
            except OSError:
                pass


class VerifiedCustody:
    """Verified, descriptor-bound files; call :meth:`close` when finished."""

    def __init__(self, *, selector: str, platform_role: str, source_commit: str, successor_manifest_sha256: str, candidate: MaterializedIdentity, receipt: MaterializedIdentity, transfer_kind: str, custody_policy: str = "declared-custody-no-execution", causal_build_attestation: bool = False) -> None:
        self.selector, self.platform_role, self.source_commit = selector, platform_role, source_commit
        self.successor_manifest_sha256 = successor_manifest_sha256
        self.candidate, self.receipt, self.transfer_kind = candidate, receipt, transfer_kind
        self.custody_policy, self.causal_build_attestation = custody_policy, causal_build_attestation

    @property
    def candidate_fd(self) -> int:
        return self.candidate.fd

    @property
    def receipt_fd(self) -> int:
        return self.receipt.fd

    @property
    def candidate_bytes(self) -> int:
        return self.candidate.bytes

    @property
    def candidate_sha256(self) -> str:
        return self.candidate.sha256

    @property
    def candidate_path(self) -> Path:
        return self.candidate.path

    @property
    def receipt_path(self) -> Path:
        return self.receipt.path

    def close(self) -> None:
        for identity in (self.candidate, self.receipt):
            identity.close()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CustodyError("duplicate-json-key", key)
        result[key] = value
    return result


def _constant(token: str) -> None:
    raise CustodyError("nonfinite-json", token)


def _depth(value: Any, depth: int = 0) -> None:
    if depth > MAX_JSON_DEPTH:
        raise CustodyError("json-depth", "JSON exceeds the bounded nesting depth")
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise CustodyError("json-key", "JSON object key is not a string")
            _depth(child, depth + 1)
    elif isinstance(value, list):
        for child in value:
            _depth(child, depth + 1)


def _json(raw: bytes, label: str, limit: int) -> Any:
    if not isinstance(raw, bytes) or len(raw) == 0 or len(raw) > limit:
        raise CustodyError("json-size", f"{label} is absent or exceeds its limit")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_constant)
    except CustodyError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as error:
        raise CustodyError("malformed-json", f"{label}: {error}") from error
    _depth(value)
    return value


def _exact_keys(value: Any, keys: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != keys:
        raise CustodyError("schema", f"{label} has missing or unexpected fields")


def _string(value: Any, label: str, *, max_bytes: int = 4096) -> str:
    if type(value) is not str or not value or "\x00" in value or len(value.encode("utf-8")) > max_bytes:
        raise CustodyError("field", f"{label} is not a bounded string")
    return value


def _sha(value: Any, label: str) -> str:
    if type(value) is not str or not SHA_RE.fullmatch(value):
        raise CustodyError("digest", f"{label} is not a lowercase SHA-256 digest")
    return value


def _commit(value: Any, label: str) -> str:
    if type(value) is not str or not COMMIT_RE.fullmatch(value):
        raise CustodyError("commit", f"{label} is not a lowercase full Git SHA")
    return value


def _positive_int(value: Any, label: str, maximum: int = 2**63 - 1) -> int:
    if type(value) is not int or isinstance(value, bool) or value <= 0 or value > maximum:
        raise CustodyError("field", f"{label} is not a bounded positive integer")
    return value


def _nonnegative_int(value: Any, label: str, maximum: int = MAX_BUNDLE_BYTES) -> int:
    if type(value) is not int or isinstance(value, bool) or value < 0 or value > maximum:
        raise CustodyError("field", f"{label} is not a bounded integer")
    return value


def _safe_relative(value: Any, label: str) -> str:
    path = _string(value, label)
    if path.startswith("/") or path.startswith("./") or "\\" in path:
        raise CustodyError("path", f"{label} is unsafe")
    parts = path.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise CustodyError("path", f"{label} contains traversal or empty component")
    return path


def _timestamp(value: Any, label: str) -> _dt.datetime:
    text = _string(value, label, max_bytes=32)
    if not ISO_RE.fullmatch(text):
        raise CustodyError("lineage-time", f"{label} is not UTC second precision")
    try:
        return _dt.datetime.fromisoformat(text[:-1]).replace(tzinfo=_dt.timezone.utc)
    except ValueError as error:
        raise CustodyError("lineage-time", f"{label} is not a valid UTC time") from error


def _now(value: Any | None) -> _dt.datetime:
    if value is None:
        return _dt.datetime.now(_dt.timezone.utc)
    if isinstance(value, _dt.datetime):
        if value.tzinfo is None:
            raise CustodyError("clock", "now must be timezone-aware")
        return value.astimezone(_dt.timezone.utc)
    if isinstance(value, str):
        return _timestamp(value, "now")
    raise CustodyError("clock", "now must be timezone-aware datetime or UTC string")


def _identity(value: Any, label: str, *, mode: int | None = None, max_bytes: int = MAX_BUNDLE_BYTES) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CustodyError("identity", f"{label} is not an object")
    expected = {"bytes", "sha256"} if mode is None else {"bytes", "mode", "sha256"}
    _exact_keys(value, expected, label)
    size = _nonnegative_int(value["bytes"], f"{label}.bytes", max_bytes)
    if size == 0:
        raise CustodyError("identity", f"{label}.bytes must be positive")
    digest = _sha(value["sha256"], f"{label}.sha256")
    result = {"bytes": size, "sha256": digest}
    if mode is not None:
        if type(value["mode"]) is not int or stat.S_IMODE(value["mode"]) != mode or not stat.S_ISREG(value["mode"]):
            raise CustodyError("identity", f"{label}.mode is not the expected regular-file mode")
        result["mode"] = value["mode"]
    return result


def _manifest_file_identity(value: Any, label: str, *, max_bytes: int = MAX_METADATA_BYTES) -> None:
    """Validate freeze identities, whose mode is recorded as permissions."""
    if not isinstance(value, Mapping):
        raise CustodyError("identity", f"{label} is not an object")
    _exact_keys(value, {"bytes", "mode", "path", "sha256"}, label)
    _positive_int(value["bytes"], f"{label}.bytes", max_bytes)
    _sha(value["sha256"], f"{label}.sha256")
    if type(value["mode"]) is not int or value["mode"] != 0o644:
        raise CustodyError("identity", f"{label}.mode is not regular 0644")


def _sibling_identity(manifest: Mapping[str, Any], path: str) -> dict[str, Any] | None:
    for field in ("runtime_tool_identities", "exact_runtime_tool_identities", "provenance_tool_identities"):
        identities = manifest.get(field)
        if isinstance(identities, list):
            for identity in identities:
                if isinstance(identity, Mapping) and identity.get("path") == path:
                    return dict(identity)
    return None


def _read_sibling_bytes(path: Path, label: str, *, expected: Mapping[str, Any] | None = None) -> bytes:
    """Read a validator sibling from stable descriptor-bound bytes."""
    absolute = Path(path).absolute()
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    directory_flags = flags | getattr(os, "O_DIRECTORY", 0)
    parent = -1
    descriptor = -1
    try:
        parent = os.open(os.sep, directory_flags)
        for component in absolute.parts[1:-1]:
            child = os.open(component, directory_flags, dir_fd=parent)
            os.close(parent)
            parent = child
        name = absolute.parts[-1]
        before_path = os.stat(name, dir_fd=parent, follow_symlinks=False)
        if stat.S_ISLNK(before_path.st_mode) or not stat.S_ISREG(before_path.st_mode) or stat.S_IMODE(before_path.st_mode) != 0o644 or before_path.st_nlink != 1:
            raise CustodyError("validator", f"{label} is not a mode-0644 single-link file")
        if before_path.st_size <= 0 or before_path.st_size > 16 * 1024 * 1024:
            raise CustodyError("validator", f"{label} is outside its bounded size")
        if expected is not None and (expected.get("mode") != 0o644 or expected.get("bytes") != before_path.st_size):
            raise CustodyError("validator", f"{label} differs from its frozen size or mode")
        descriptor = os.open(name, flags, dir_fd=parent)
        opened = os.fstat(descriptor)
        identity = lambda info: (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
        if identity(opened) != identity(before_path):
            raise CustodyError("validator", f"{label} changed before reading")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(1024 * 1024, 16 * 1024 * 1024 + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > 16 * 1024 * 1024:
                raise CustodyError("validator", f"{label} grew beyond its bound")
        raw = b"".join(chunks)
        after = os.fstat(descriptor)
        after_path = os.stat(name, dir_fd=parent, follow_symlinks=False)
        if identity(after) != identity(before_path) or identity(after_path) != identity(after) or len(raw) != before_path.st_size:
            raise CustodyError("validator", f"{label} changed while reading")
        if expected is not None and (len(raw) != expected.get("bytes") or hashlib.sha256(raw).hexdigest() != expected.get("sha256")):
            raise CustodyError("validator", f"{label} differs from its frozen identity")
        return raw
    except CustodyError:
        raise
    except OSError as error:
        raise CustodyError("validator", f"cannot read {label}") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if parent >= 0:
            os.close(parent)


def _load_module_from_bytes(module_name: str, path: Path, source: bytes) -> Any:
    try:
        code = compile(source, str(path), "exec", dont_inherit=True, optimize=0)
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
        return module
    except CustodyError:
        raise
    except Exception as error:
        raise CustodyError("validator", f"{module_name} cannot be loaded") from error


def _load_freeze_validator(raw: bytes) -> Any:
    bootstrap = _json(raw, "successor freeze manifest", MAX_JSON_BYTES)
    expected = _sibling_identity(bootstrap, "scripts/phase3_freeze_manifest.py") if isinstance(bootstrap, Mapping) else None
    if expected is None:
        raise CustodyError("manifest-closure", "successor freeze does not authenticate its canonical validator")
    path = Path(__file__).with_name("phase3_freeze_manifest.py")
    source = _read_sibling_bytes(path, "canonical freeze validator", expected=expected)
    return _load_module_from_bytes("phase3_exact_custody_freeze", path, source)


def _parse_manifest(expected_manifest: bytes | Mapping[str, Any]) -> dict[str, Any]:
    """Authenticate exact bytes through the canonical freeze owner."""
    if not isinstance(expected_manifest, bytes):
        raise CustodyError("manifest", "successor freeze manifest must be supplied as exact bytes")
    try:
        bootstrap = _json(expected_manifest, "successor freeze manifest", MAX_JSON_BYTES)
    except CustodyError:
        raise
    if not isinstance(bootstrap, Mapping) or bootstrap.get("schema") != FREEZE_SCHEMA:
        raise CustodyError("manifest-version", "exact custody requires the current freeze-manifest-5 contract")
    try:
        freeze = _load_freeze_validator(expected_manifest)
        value = freeze.validate_manifest(expected_manifest)
    except Exception as error:
        raise CustodyError("manifest", f"canonical freeze validator rejected successor bytes: {error}") from error
    if value.get("schema") != FREEZE_SCHEMA:
        raise CustodyError("manifest-version", "exact custody requires the current freeze-manifest-5 contract")
    exact_tools = value.get("exact_runtime_tool_identities")
    if type(exact_tools) is not list or tuple(item.get("path") for item in exact_tools if isinstance(item, Mapping)) != REQUIRED_EXACT_RUNTIME_TOOLS:
        raise CustodyError("manifest-closure", "v5 freeze does not bind the closed launcher exact-runtime tool set")
    for index, identity in enumerate(exact_tools):
        _manifest_file_identity(identity, f"manifest.exact_runtime_tool_identities[{index}]")
    for field, expected_paths in (
        ("runtime_tool_identities", REQUIRED_RUNTIME_TOOLS),
        ("provenance_tool_identities", REQUIRED_PROVENANCE_TOOLS),
    ):
        collection = value.get(field)
        if type(collection) is not list or tuple(item.get("path") for item in collection if isinstance(item, Mapping)) != expected_paths:
            raise CustodyError("manifest-closure", f"v5 freeze does not bind the closed {field} set")
        for index, identity in enumerate(collection):
            _manifest_file_identity(identity, f"manifest.{field}[{index}]")
    if len(REQUIRED_RUNTIME_TOOLS) + len(REQUIRED_EXACT_RUNTIME_TOOLS) + len(REQUIRED_PROVENANCE_TOOLS) != 21:
        raise CustodyError("manifest-closure", "v5 runtime/provenance tool contract has an invalid total")
    if value.get("experiment_closure_schema") != EXPERIMENT_CLOSURE_SCHEMA:
        raise CustodyError("manifest-closure", "successor freeze does not bind the current experiment-closure schema")
    closure_tools = value.get("experiment_closure_tool_identities")
    if type(closure_tools) is not list or len(closure_tools) != 1:
        raise CustodyError("manifest-closure", "successor freeze closure tool identity is not a singleton list")
    closure_tool = closure_tools[0]
    _manifest_file_identity(closure_tool, "manifest.experiment_closure_tool_identities[0]")
    if closure_tool["path"] != EXPERIMENT_CLOSURE_TOOL:
        raise CustodyError("manifest-closure", "successor freeze closure tool path is not canonical")
    return value


def _manifest_binding(manifest: Mapping[str, Any], expected_hash: str, selector: str) -> dict[str, Any]:
    _sha(expected_hash, "expected successor freeze hash")
    if manifest.get("manifest_sha256") is not None and manifest.get("manifest_sha256") != expected_hash:
        raise CustodyError("manifest", "expected successor freeze hash does not match manifest")
    binding = manifest["binding"]
    source = manifest.get("candidate_source_commit")
    if source is None:
        raise CustodyError("manifest", "successor freeze source commit is unavailable")
    source = _commit(source, "manifest.candidate_source_commit")
    binaries = manifest.get("binaries")
    if not isinstance(binaries, Mapping) or selector not in binaries:
        raise CustodyError("manifest", "successor freeze binary slot is unavailable")
    slot = binaries[selector]
    if not isinstance(slot, Mapping):
        raise CustodyError("manifest", "successor freeze binary slot is malformed")
    status = slot.get("status")
    if status is not None and status != "bound":
        raise CustodyError("manifest", "successor freeze binary slot is not bound")
    identity = slot.get("binary_identity")
    if not isinstance(identity, Mapping):
        raise CustodyError("manifest", "successor freeze binary identity is unavailable")
    # Freeze mode is a full st_mode integer.  Keep only the required regular
    # executable identity while rejecting malformed modes.
    expected_binary = _identity(identity, "manifest.binary_identity", mode=0o755, max_bytes=MAX_CANDIDATE_BYTES)
    receipt_sha = slot.get("receipt_sha256")
    receipt_self = slot.get("receipt_self_hash")
    if receipt_sha is None or receipt_self is None:
        raise CustodyError("manifest", "successor freeze receipt identities are unavailable")
    repository_inputs = manifest["repository_inputs"]
    workflow = repository_inputs["native_build_workflow"]
    if workflow.get("path") != WORKFLOW_PATH:
        raise CustodyError("manifest", "successor freeze workflow path is not the Gate-B build workflow")
    identity = workflow["identity"]
    if identity.get("path") != workflow["path"]:
        raise CustodyError("manifest", "successor freeze workflow identity path differs from its declared path")
    workflow_identity = {
        "path": _safe_relative(workflow["path"], "manifest.workflow.path"),
        "sha256": _sha(identity["sha256"], "manifest.workflow.sha256"),
    }
    return {"source_commit": source, "binary": expected_binary, "receipt_bytes": slot["receipt_bytes"], "receipt_sha256": _sha(receipt_sha, "manifest.receipt_sha256"), "receipt_self_hash": _sha(receipt_self, "manifest.receipt_self_hash"), "workflow": workflow_identity}


def _validate_lineage(transfer: Mapping[str, Any], now: _dt.datetime) -> None:
    kind = transfer.get("kind")
    if kind == "invocation-owned-raw-bundle-tar":
        required = {"kind", "locator", "bundle", "created_at", "expires_at", "retention_days"}
        _exact_keys(transfer, required, "transfer")
        locator = transfer["locator"]
        if not isinstance(locator, Mapping):
            raise CustodyError("locator", "raw locator is malformed")
        _exact_keys(locator, {"kind", "value"}, "transfer.locator")
        if locator["kind"] != "filesystem-path":
            raise CustodyError("locator", "raw locator kind is not invocation-owned filesystem data")
        locator_value = _string(locator["value"], "transfer.locator.value", max_bytes=16 * 1024)
        if not Path(locator_value).is_absolute():
            raise CustodyError("locator", "transfer locator must be an absolute anchored path")
        _identity(transfer["bundle"], "transfer.bundle", max_bytes=MAX_BUNDLE_BYTES)
    elif kind == "github-actions-artifact-zip":
        required = {"kind", "locator", "workflow", "run", "artifact", "archive", "bundle"}
        _exact_keys(transfer, required, "transfer")
        locator = transfer["locator"]
        if not isinstance(locator, Mapping):
            raise CustodyError("locator", "GitHub locator is malformed")
        _exact_keys(locator, {"kind", "value"}, "transfer.locator")
        if locator["kind"] != "filesystem-path":
            raise CustodyError("locator", "GitHub locator must identify supplied bytes")
        locator_value = _string(locator["value"], "transfer.locator.value", max_bytes=16 * 1024)
        if not Path(locator_value).is_absolute():
            raise CustodyError("locator", "transfer locator must be an absolute anchored path")
        workflow = transfer["workflow"]
        if not isinstance(workflow, Mapping):
            raise CustodyError("lineage", "workflow lineage is malformed")
        _exact_keys(workflow, {"path", "commit", "sha256"}, "transfer.workflow")
        if _safe_relative(workflow["path"], "transfer.workflow.path") != WORKFLOW_PATH:
            raise CustodyError("lineage", "workflow path is not the frozen Gate-B workflow")
        _commit(workflow["commit"], "transfer.workflow.commit")
        _sha(workflow["sha256"], "transfer.workflow.sha256")
        run = transfer["run"]
        if not isinstance(run, Mapping):
            raise CustodyError("lineage", "workflow run lineage is malformed")
        _exact_keys(run, {"id", "attempt"}, "transfer.run")
        _positive_int(run["id"], "transfer.run.id")
        _positive_int(run["attempt"], "transfer.run.attempt", 10000)
        artifact = transfer["artifact"]
        if not isinstance(artifact, Mapping):
            raise CustodyError("lineage", "artifact lineage is malformed")
        _exact_keys(artifact, {"id", "digest", "created_at", "expires_at", "retention_days"}, "transfer.artifact")
        _positive_int(artifact["id"], "transfer.artifact.id")
        digest = _string(artifact["digest"], "transfer.artifact.digest", max_bytes=80)
        if not (SHA_RE.fullmatch(digest) or (digest.startswith("sha256:") and SHA_RE.fullmatch(digest[7:]))):
            raise CustodyError("digest", "GitHub artifact digest is malformed")
        _identity(transfer["archive"], "transfer.archive", max_bytes=MAX_ZIP_BYTES)
        _identity(transfer["bundle"], "transfer.bundle", max_bytes=MAX_BUNDLE_BYTES)
    else:
        raise CustodyError("transfer", "unsupported transfer kind")
    created = _timestamp(transfer.get("created_at", transfer.get("artifact", {}).get("created_at")), "transfer.created_at")
    expires = _timestamp(transfer.get("expires_at", transfer.get("artifact", {}).get("expires_at")), "transfer.expires_at")
    retention = transfer.get("retention_days", transfer.get("artifact", {}).get("retention_days"))
    _positive_int(retention, "transfer.retention_days", 3650)
    if expires <= created or expires <= now or created > now:
        raise CustodyError("expired", "transfer is stale, not yet valid, or expired")
    window = expires - created
    if window > _dt.timedelta(days=retention):
        raise CustodyError("retention", "transfer expiry exceeds its declared retention window")
    if kind == "github-actions-artifact-zip" and retention != GITHUB_RETENTION_DAYS:
        raise CustodyError("retention", "GitHub artifact retention must match the frozen workflow declaration")


def _validate_record(record: Mapping[str, Any], expected_manifest: bytes | Mapping[str, Any], expected_hash: str, now: Any | None) -> tuple[dict[str, Any], dict[str, Any]]:
    required = {"schema", "experiment_id", "phase_id", "candidate_profile_id", "successor_manifest_sha256", "platform", "candidate_source_commit", "receipt", "candidate", "transfer", "policy", "custody_record_sha256"}
    _exact_keys(record, required, "custody record")
    if record["schema"] != SCHEMA or record["experiment_id"] != EXPERIMENT_ID or record["phase_id"] != PHASE_ID or record["candidate_profile_id"] != CANDIDATE_PROFILE_ID:
        raise CustodyError("record-binding", "custody record fixed identity is wrong")
    expected_hash = _sha(expected_hash, "expected successor freeze hash")
    if record["successor_manifest_sha256"] != expected_hash:
        raise CustodyError("record-binding", "custody record is bound to a different successor freeze")
    manifest = _parse_manifest(expected_manifest)
    selector_obj = record["platform"]
    _exact_keys(selector_obj, {"selector", "role"}, "record.platform")
    selector = _string(selector_obj["selector"], "record.platform.selector")
    role = _string(selector_obj["role"], "record.platform.role")
    if selector not in PLATFORM_SELECTORS or role != PLATFORM_SELECTORS[selector]:
        raise CustodyError("platform", "platform selector/role is unsupported")
    binding = _manifest_binding(manifest, expected_hash, selector)
    source = _commit(record["candidate_source_commit"], "record.candidate_source_commit")
    if source != binding["source_commit"]:
        raise CustodyError("source", "record source commit differs from successor freeze")
    receipt = record["receipt"]
    _exact_keys(receipt, {"path", "mode", "bytes", "sha256", "self_hash"}, "record.receipt")
    if _safe_relative(receipt["path"], "record.receipt.path") != "build-receipt.json":
        raise CustodyError("receipt", "receipt path is not the fixed bundle member")
    if type(receipt["mode"]) is not int or stat.S_IMODE(receipt["mode"]) != 0o644 or not stat.S_ISREG(receipt["mode"]):
        raise CustodyError("receipt", "receipt mode is not regular 0644")
    receipt_id = _identity({"bytes": receipt["bytes"], "sha256": receipt["sha256"]}, "record.receipt", max_bytes=MAX_RECEIPT_BYTES)
    receipt_self = _sha(receipt["self_hash"], "record.receipt.self_hash")
    if receipt["bytes"] != binding["receipt_bytes"] or receipt_id["sha256"] != binding["receipt_sha256"] or receipt_self != binding["receipt_self_hash"]:
        raise CustodyError("receipt", "receipt identity differs from successor freeze")
    candidate = record["candidate"]
    _exact_keys(candidate, {"path", "mode", "bytes", "sha256"}, "record.candidate")
    if _safe_relative(candidate["path"], "record.candidate.path") != "candidate":
        raise CustodyError("candidate", "candidate path is not the fixed bundle member")
    candidate_id = _identity({key: candidate[key] for key in ("bytes", "mode", "sha256")}, "record.candidate", mode=0o755, max_bytes=MAX_CANDIDATE_BYTES)
    if candidate_id != binding["binary"]:
        raise CustodyError("candidate", "candidate identity differs from successor freeze")
    policy = record["policy"]
    _exact_keys(policy, {"custody", "candidate_execution", "experiment_dispatch", "causal_build_attestation"}, "record.policy")
    if policy != {"custody": "declared", "candidate_execution": "prohibited", "experiment_dispatch": "prohibited", "causal_build_attestation": False}:
        raise CustodyError("policy", "custody policy does not distinguish declared custody from causal attestation")
    _validate_lineage(record["transfer"], _now(now))
    transfer = record["transfer"]
    if (role == "wsl") != (transfer["kind"] == "invocation-owned-raw-bundle-tar"):
        raise CustodyError("platform", "transfer form does not match platform role")
    if transfer["kind"] == "github-actions-artifact-zip":
        if transfer["workflow"]["commit"] != source:
            raise CustodyError("lineage", "workflow commit does not bind candidate source commit")
        workflow_identity = binding.get("workflow")
        if workflow_identity is not None and transfer["workflow"]["sha256"] != workflow_identity["sha256"]:
            raise CustodyError("lineage", "workflow file digest differs from successor freeze")
    self_hash = _sha(record["custody_record_sha256"], "record.custody_record_sha256")
    unsigned = dict(record)
    unsigned["custody_record_sha256"] = None
    if hashlib.sha256(SELF_HASH_DOMAIN + _canonical(unsigned)).hexdigest() != self_hash:
        raise CustodyError("record-hash", "custody record self-hash does not match canonical contents")
    return {"selector": selector, "role": role, "source_commit": source, "receipt": receipt, "candidate": candidate, "transfer": record["transfer"], "manifest": manifest, "binding": binding}, record["transfer"]


def encode_custody_record(record: Mapping[str, Any]) -> bytes:
    """Canonicalize and self-hash a custody record supplied by a recorder."""
    value = dict(record)
    value["custody_record_sha256"] = None
    raw = _canonical(value)
    value["custody_record_sha256"] = hashlib.sha256(SELF_HASH_DOMAIN + raw).hexdigest()
    encoded = _canonical(value) + b"\n"
    if len(encoded) > MAX_RECORD_BYTES:
        raise CustodyError("record-size", "custody record exceeds the bounded size")
    return encoded


def _expected_hash(expected_manifest_sha256: str | None, expected_manifest_hash: str | None) -> str:
    if expected_manifest_sha256 is None:
        expected_manifest_sha256 = expected_manifest_hash
    elif expected_manifest_hash is not None and expected_manifest_hash != expected_manifest_sha256:
        raise CustodyError("manifest", "successor manifest hashes disagree")
    if expected_manifest_sha256 is None:
        raise CustodyError("manifest", "expected successor freeze hash is unavailable")
    return expected_manifest_sha256


def validate_custody_record(raw_or_record: bytes | Mapping[str, Any], *, expected_manifest: bytes | Mapping[str, Any], expected_manifest_sha256: str | None = None, expected_manifest_hash: str | None = None, now: Any | None = None) -> dict[str, Any]:
    """Validate a record without consuming transfer bytes or writing files."""
    if isinstance(raw_or_record, bytes):
        if len(raw_or_record) > MAX_RECORD_BYTES or not raw_or_record.endswith(b"\n"):
            raise CustodyError("record", "record is absent, too large, or not canonical")
        value = _json(raw_or_record, "custody record", MAX_RECORD_BYTES)
        if raw_or_record != _canonical(value) + b"\n":
            raise CustodyError("record", "record is not canonical JSON")
    else:
        value = dict(raw_or_record)
        _depth(value)
    validated, _ = _validate_record(value, expected_manifest, _expected_hash(expected_manifest_sha256, expected_manifest_hash), now)
    return validated


def _open_anchored_parent(path: Path, label: str) -> tuple[int, str, Path]:
    """Walk a path with openat/O_NOFOLLOW and return its anchored parent fd."""
    absolute = path.absolute()
    if not absolute.is_absolute() or len(absolute.parts) < 2:
        raise CustodyError("path", f"{label} is not a file path")
    if any(part in {"", ".", ".."} or "\x00" in part or "\\" in part for part in absolute.parts[1:]):
        raise CustodyError("path", f"{label} contains an unsafe component")
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        parent_fd = os.open(os.sep, flags)
    except OSError as error:
        raise CustodyError("unavailable", f"{label}: {error}") from error
    try:
        for component in absolute.parts[1:-1]:
            next_fd = os.open(component, flags, dir_fd=parent_fd)
            os.close(parent_fd)
            parent_fd = next_fd
    except OSError as error:
        os.close(parent_fd)
        raise CustodyError("unavailable", f"{label}: {error}") from error
    return parent_fd, absolute.parts[-1], absolute


def _checked_read(path: Path, label: str, limit: int) -> tuple[bytes, int]:
    """Read a single-link regular path through an anchored descriptor."""
    parent_fd, name, _ = _open_anchored_parent(path, label)
    fd = None
    try:
        before_path = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if stat.S_ISLNK(before_path.st_mode) or not stat.S_ISREG(before_path.st_mode) or before_path.st_nlink != 1:
            raise CustodyError("path-type", f"{label} is not a single-link regular file")
        fd = os.open(name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0), dir_fd=parent_fd)
        before = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_mode, before.st_nlink, before.st_size) != (before_path.st_dev, before_path.st_ino, before_path.st_mode, before_path.st_nlink, before_path.st_size):
            raise CustodyError("race", f"{label} changed while opening")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(fd, min(1024 * 1024, limit - total + 1))
            if not chunk:
                break
            total += len(chunk)
            if total > limit:
                raise CustodyError("size", f"{label} exceeds its bound")
            chunks.append(chunk)
        after = os.fstat(fd)
        after_path = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if (before.st_dev, before.st_ino, before.st_mode, before.st_nlink, before.st_size) != (after.st_dev, after.st_ino, after.st_mode, after.st_nlink, after.st_size) or (after_path.st_dev, after_path.st_ino, after_path.st_mode, after_path.st_nlink, after_path.st_size) != (after.st_dev, after.st_ino, after.st_mode, after.st_nlink, after.st_size):
            raise CustodyError("race", f"{label} changed while reading")
        return b"".join(chunks), stat.S_IMODE(after.st_mode)
    except CustodyError:
        raise
    except OSError as error:
        raise CustodyError("unavailable", f"{label}: {error}") from error
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parent_fd)


def _zip_bundle(raw: bytes, transfer: Mapping[str, Any]) -> bytes:
    if len(raw) != transfer["archive"]["bytes"] or hashlib.sha256(raw).hexdigest() != transfer["archive"]["sha256"]:
        raise CustodyError("archive-mismatch", "GitHub artifact ZIP identity differs from custody record")
    artifact_digest = transfer["artifact"]["digest"]
    artifact_hex = artifact_digest[7:] if artifact_digest.startswith("sha256:") else artifact_digest
    if hashlib.sha256(raw).hexdigest() != artifact_hex:
        raise CustodyError("archive-mismatch", "GitHub artifact digest does not bind the supplied ZIP")
    try:
        zf = zipfile.ZipFile(io.BytesIO(raw), "r")
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        raise CustodyError("container", f"artifact is not a valid ZIP: {error}") from error
    try:
        infos = zf.infolist()
        if len(infos) != 1:
            raise CustodyError("container-closure", "GitHub artifact ZIP must contain exactly one member")
        info = infos[0]
        name = info.filename
        if not name or name != Path(name).name or name in {".", ".."} or not name.endswith(".tar") or "\\" in name or "\x00" in name:
            raise CustodyError("container-path", "artifact ZIP member is not one safe bundle tar")
        if info.is_dir() or info.file_size > MAX_BUNDLE_BYTES or info.compress_size > MAX_ZIP_BYTES:
            raise CustodyError("container-size", "artifact ZIP member is too large or a directory")
        mode = (info.external_attr >> 16) & 0o170000
        if mode and mode != stat.S_IFREG:
            raise CustodyError("container-type", "artifact ZIP member is not a regular file")
        if info.flag_bits & 0x1:
            raise CustodyError("container", "encrypted ZIP members are unavailable")
        if info.compress_size and info.file_size > info.compress_size * MAX_ZIP_RATIO:
            raise CustodyError("container-bomb", "artifact ZIP compression ratio exceeds the bound")
        try:
            bundle = zf.read(info)
        except (OSError, RuntimeError, zipfile.BadZipFile) as error:
            raise CustodyError("container", f"artifact ZIP member cannot be consumed: {error}") from error
        if len(bundle) != info.file_size:
            raise CustodyError("container", "artifact ZIP member size changed")
    finally:
        zf.close()
    # zipfile accepts trailing data after EOCD; reject it explicitly.  EOCD
    # comments are valid and included in the exact supplied archive identity.
    marker = raw.rfind(b"PK\x05\x06")
    if marker < 0 or marker + 22 > len(raw):
        raise CustodyError("container", "artifact ZIP lacks a canonical end record")
    comment_len = int.from_bytes(raw[marker + 20:marker + 22], "little")
    if marker + 22 + comment_len != len(raw):
        raise CustodyError("container", "artifact ZIP has trailing or truncated bytes")
    if len(bundle) != transfer["bundle"]["bytes"] or hashlib.sha256(bundle).hexdigest() != transfer["bundle"]["sha256"]:
        raise CustodyError("archive-mismatch", "inner bundle tar identity differs from custody record")
    return bundle


def _tar_members(raw: bytes, transfer: Mapping[str, Any]) -> dict[str, bytes]:
    if len(raw) != transfer["bundle"]["bytes"] or hashlib.sha256(raw).hexdigest() != transfer["bundle"]["sha256"]:
        raise CustodyError("archive-mismatch", "bundle tar identity differs from custody record")
    if len(raw) > MAX_BUNDLE_BYTES or len(raw) < 10240 or len(raw) % 512:
        raise CustodyError("tar-size", "bundle tar is unavailable or has an invalid bounded size")
    try:
        tf = tarfile.open(fileobj=io.BytesIO(raw), mode="r:")
        members = tf.getmembers()
    except (OSError, tarfile.TarError) as error:
        raise CustodyError("tar", f"bundle tar is malformed: {error}") from error
    if len(members) != MAX_BUNDLE_MEMBERS:
        raise CustodyError("tar-closure", "bundle tar must contain exactly five members")
    result: dict[str, bytes] = {}
    cursor = 0
    try:
        for index, member in enumerate(members):
            expected_name = BUNDLE_MEMBERS[index]
            if member.name != expected_name or "/" in member.name or "\\" in member.name or member.name in result:
                raise CustodyError("tar-path", "bundle tar member name/order is unsafe")
            if member.offset != cursor:
                raise CustodyError("tar-order", "bundle tar has noncanonical member offsets")
            if member.type not in (tarfile.REGTYPE, tarfile.AREGTYPE) or member.issym() or member.islnk() or member.isdir() or member.isdev() or member.size < 0:
                raise CustodyError("tar-type", "bundle tar contains a link, directory, device, or special member")
            expected_mode = 0o755 if member.name == "candidate" else 0o644
            if stat.S_IMODE(member.mode) != expected_mode:
                raise CustodyError("tar-mode", f"bundle member {member.name} has the wrong mode")
            limit = MAX_CANDIDATE_BYTES if member.name == "candidate" else MAX_RECEIPT_BYTES if member.name == "build-receipt.json" else MAX_METADATA_BYTES if member.name == "build-metadata.json" else MAX_CARGO_BYTES if member.name == "cargo-metadata.json" else 64 * 1024
            if member.size > min(limit, MAX_MEMBER_BYTES):
                raise CustodyError("tar-size", f"bundle member {member.name} exceeds its bound")
            extractor = tf.extractfile(member)
            if extractor is None:
                raise CustodyError("tar-member", f"bundle member {member.name} cannot be read")
            data = extractor.read(member.size + 1)
            if len(data) != member.size:
                raise CustodyError("tar-member", f"bundle member {member.name} changed or is truncated")
            result[member.name] = data
            cursor = member.offset_data + ((member.size + 511) // 512) * 512
    finally:
        tf.close()
    if cursor >= len(raw) or len(raw) - cursor < 1024 or len(raw) - cursor > MAX_TAR_TRAILING_BYTES or any(raw[cursor:]):
        raise CustodyError("tar-container", "bundle tar has noncanonical trailing data")
    return result


def _validate_sums(data: bytes, members: Mapping[str, bytes]) -> None:
    if len(data) > 64 * 1024:
        raise CustodyError("sums-size", "SHA256SUMS is too large")
    try:
        text = data.decode("ascii")
    except UnicodeDecodeError as error:
        raise CustodyError("sums", "SHA256SUMS is not ASCII") from error
    lines = text.splitlines(keepends=True)
    if len(lines) != len(MANIFEST_MEMBERS) or any(not line.endswith("\n") for line in lines):
        raise CustodyError("sums", "SHA256SUMS must contain exactly four newline-terminated lines")
    for line, name in zip(lines, MANIFEST_MEMBERS):
        expected_prefix = hashlib.sha256(members[name]).hexdigest() + "  " + name + "\n"
        if line != expected_prefix:
            raise CustodyError("sums", f"SHA256SUMS does not exactly bind {name}")


def _load_receipt_validator(manifest: Mapping[str, Any] | None = None) -> Any:
    path = Path(__file__).with_name("phase3_build_receipt.py")
    expected = _sibling_identity(manifest, "scripts/phase3_build_receipt.py") if manifest is not None else None
    if manifest is not None and expected is None:
        raise CustodyError("receipt", "successor freeze does not authenticate its receipt validator")
    source = _read_sibling_bytes(path, "build receipt validator", expected=expected)
    return _load_module_from_bytes("phase3_exact_custody_receipt", path, source)


def _validate_metadata(
    members: Mapping[str, bytes],
    role: str,
    source: str,
    manifest: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    receipt_raw = members["build-receipt.json"]
    if len(receipt_raw) > MAX_RECEIPT_BYTES:
        raise CustodyError("receipt-size", "build receipt is too large")
    try:
        module = _load_receipt_validator(manifest)
        receipt = module.validate_receipt(receipt_raw)
    except CustodyError:
        raise
    except Exception as error:
        raise CustodyError("receipt", f"build receipt is malformed or unavailable: {error}") from error
    if receipt["phase_id"] != PHASE_ID or receipt["candidate_profile_id"] != CANDIDATE_PROFILE_ID or receipt["source_commit"] != source or receipt["mode"] != "build-only" or receipt["execution_permitted"] is not False:
        raise CustodyError("receipt-binding", "build receipt has wrong phase/profile/source or execution policy")
    build = receipt["build"]
    if build["platform_role"] != role or build["target"] != TARGET or build["profile"] != PROFILE:
        raise CustodyError("receipt-binding", "build receipt has wrong platform slot/target/profile")
    metadata = _json(members["build-metadata.json"], "build metadata", MAX_METADATA_BYTES)
    if not isinstance(metadata, dict):
        raise CustodyError("metadata", "build metadata is not an object")
    expected_metadata = {"schema", "source_commit", "candidate_profile_id", "platform_role", "target", "profile", "platform_observation", "build"}
    if set(metadata) != expected_metadata or metadata["schema"] != METADATA_SCHEMA or metadata["source_commit"] != source or metadata["candidate_profile_id"] != CANDIDATE_PROFILE_ID or metadata["platform_role"] != role or metadata["target"] != TARGET or metadata["profile"] != PROFILE:
        raise CustodyError("metadata-binding", "build metadata has wrong identity or fields")
    observation = metadata["platform_observation"]
    if not isinstance(observation, dict) or set(observation) != {"stability", "runner_os", "runner_arch", "image_os", "image_version", "kernel", "sanitized_environment_keys"} or not isinstance(observation["sanitized_environment_keys"], list) or any(type(item) is not str for item in observation["sanitized_environment_keys"]):
        raise CustodyError("metadata-binding", "build metadata platform observation is malformed")
    metadata_build = metadata["build"]
    required_build = {"argv", "cwd", "env_policy", "toolchain", "cargo_lock_path", "dependency_metadata_path", "vendor_path", "vendor_role_path", "cargo_config_path", "cargo_config_role_path", "binary_role_path"}
    if not isinstance(metadata_build, dict) or set(metadata_build) != required_build or metadata_build.get("binary_role_path") != build["binary_role_path"]:
        raise CustodyError("metadata-binding", "build metadata binary slot differs from receipt")
    if metadata["platform_observation"] != build["platform_observation"]:
        raise CustodyError("metadata-binding", "build metadata platform observation differs from receipt")
    for field in ("argv", "cwd", "env_policy", "toolchain"):
        if metadata_build[field] != build[field]:
            raise CustodyError("metadata-binding", f"build metadata {field} differs from receipt")
    if metadata_build["cargo_lock_path"] != build["cargo_lock"]["path"]:
        raise CustodyError("metadata-binding", "build metadata Cargo.lock path differs from receipt")
    if metadata_build["vendor_role_path"] != build["vendor_closure"]["role_path"] or metadata_build["cargo_config_role_path"] != build["cargo_config"]["role_path"]:
        raise CustodyError("metadata-binding", "build metadata vendor/config role differs from receipt")
    for field in ("dependency_metadata_path", "vendor_path", "cargo_config_path"):
        _string(metadata_build[field], f"build metadata {field}", max_bytes=16 * 1024)
    cargo = _json(members["cargo-metadata.json"], "Cargo metadata", MAX_CARGO_BYTES)
    if not isinstance(cargo, dict) or type(cargo.get("version")) is not int or cargo.get("version") != 1 or not isinstance(cargo.get("packages"), list) or not isinstance(cargo.get("resolve"), dict):
        raise CustodyError("cargo-metadata", "Cargo metadata is malformed")
    dependency = build["dependency_closure"]
    if dependency["bytes"] != len(members["cargo-metadata.json"]):
        raise CustodyError("cargo-metadata", "Cargo metadata byte count differs from receipt")
    if dependency["raw_sha256"] != hashlib.sha256(members["cargo-metadata.json"]).hexdigest():
        raise CustodyError("cargo-metadata", "Cargo metadata digest differs from receipt")
    return receipt, metadata


def _fresh_directory(path: Path) -> tuple[int, os.stat_result, Path]:
    """Open an empty invocation directory by anchored component traversal."""
    absolute = path.absolute()
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        directory_fd = os.open(os.sep, flags)
    except OSError as error:
        raise CustodyError("invocation-dir", f"invocation directory is unavailable: {error}") from error
    try:
        for component in absolute.parts[1:]:
            next_fd = os.open(component, flags, dir_fd=directory_fd)
            os.close(directory_fd)
            directory_fd = next_fd
        opened = os.fstat(directory_fd)
        if not stat.S_ISDIR(opened.st_mode) or os.listdir(directory_fd):
            raise CustodyError("invocation-dir", "invocation directory is not a fresh empty directory")
    except CustodyError:
        os.close(directory_fd)
        raise
    except OSError as error:
        os.close(directory_fd)
        raise CustodyError("invocation-dir", f"cannot open invocation directory: {error}") from error
    return directory_fd, opened, absolute


def _materialize_file(dirfd: int, root: Path, name: str, data: bytes, mode: int, label: str) -> MaterializedIdentity:
    writer_fd = None
    read_fd = None
    try:
        writer_fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0), mode, dir_fd=dirfd)
        os.fchmod(writer_fd, mode)
        view = memoryview(data)
        while view:
            count = os.write(writer_fd, view)
            if count <= 0:
                raise CustodyError("materialize", f"cannot write {label}")
            view = view[count:]
        os.fsync(writer_fd)
        info = os.fstat(writer_fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != mode or info.st_size != len(data):
            raise CustodyError("materialize", f"{label} descriptor identity is wrong")
        os.close(writer_fd)
        writer_fd = None
        read_fd = os.open(name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0), dir_fd=dirfd)
        flags = fcntl.fcntl(read_fd, fcntl.F_GETFL)
        if flags & os.O_ACCMODE != os.O_RDONLY:
            raise CustodyError("materialize", f"{label} was not reopened read-only")
        reopened = os.fstat(read_fd)
        reopened_path = os.stat(name, dir_fd=dirfd, follow_symlinks=False)
        if not stat.S_ISREG(reopened.st_mode) or reopened.st_nlink != 1 or (reopened.st_dev, reopened.st_ino, reopened.st_mode, reopened.st_size) != (info.st_dev, info.st_ino, info.st_mode, info.st_size) or (reopened_path.st_dev, reopened_path.st_ino, reopened_path.st_mode, reopened_path.st_size, reopened_path.st_nlink) != (reopened.st_dev, reopened.st_ino, reopened.st_mode, reopened.st_size, reopened.st_nlink):
            raise CustodyError("race", f"{label} changed while reopening")
        digest = hashlib.sha256()
        total = 0
        while True:
            chunk = os.read(read_fd, min(1024 * 1024, len(data) - total + 1))
            if not chunk:
                break
            total += len(chunk)
            if total > len(data):
                raise CustodyError("materialize", f"{label} grew while reopening")
            digest.update(chunk)
        final = os.fstat(read_fd)
        if total != len(data) or os.lseek(read_fd, 0, os.SEEK_CUR) != len(data) or digest.hexdigest() != hashlib.sha256(data).hexdigest() or final.st_size != len(data) or final.st_nlink != 1 or stat.S_IMODE(final.st_mode) != mode:
            raise CustodyError("materialize", f"{label} reopened identity or hash is wrong")
        return MaterializedIdentity(path=root / name, fd=read_fd, mode=final.st_mode, bytes=total, sha256=digest.hexdigest())
    except CustodyError:
        if writer_fd is not None:
            os.close(writer_fd)
        if read_fd is not None:
            os.close(read_fd)
        raise
    except OSError as error:
        if writer_fd is not None:
            os.close(writer_fd)
        if read_fd is not None:
            os.close(read_fd)
        raise CustodyError("materialize", f"cannot materialize {label}: {error}") from error


def _sealed_candidate(data: bytes, diagnostic: MaterializedIdentity) -> MaterializedIdentity:
    """Return a read-only executable sealed memfd for descriptor-bound launch."""
    create = getattr(os, "memfd_create", None)
    required = ("F_ADD_SEALS", "F_GET_SEALS", "F_SEAL_WRITE", "F_SEAL_GROW", "F_SEAL_SHRINK", "F_SEAL_SEAL")
    if create is None or not hasattr(os, "MFD_CLOEXEC") or not hasattr(os, "MFD_ALLOW_SEALING") or any(not hasattr(fcntl, name) for name in required):
        raise CustodyError("unsupported", "Linux memfd sealing is unavailable")
    writer = None
    reader = None
    try:
        writer = create("ck-phase3-candidate", os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
        os.fchmod(writer, 0o755)
        view = memoryview(data)
        while view:
            count = os.write(writer, view)
            if count <= 0:
                raise CustodyError("memfd", "cannot write sealed candidate")
            view = view[count:]
        os.fsync(writer)
        seals = fcntl.F_SEAL_WRITE | fcntl.F_SEAL_GROW | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_SEAL
        fcntl.fcntl(writer, fcntl.F_ADD_SEALS, seals)
        if fcntl.fcntl(writer, fcntl.F_GET_SEALS) != seals:
            raise CustodyError("memfd", "candidate memfd seals are incomplete")
        reader = os.open(f"/proc/self/fd/{writer}", os.O_RDONLY | os.O_CLOEXEC)
        flags = fcntl.fcntl(reader, fcntl.F_GETFL)
        if flags & os.O_ACCMODE != os.O_RDONLY:
            raise CustodyError("memfd", "sealed candidate was not reopened read-only")
        info = os.fstat(reader)
        if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o755 or info.st_size != len(data) or fcntl.fcntl(reader, fcntl.F_GET_SEALS) != seals:
            raise CustodyError("memfd", "sealed candidate identity is wrong")
        digest = hashlib.sha256()
        total = 0
        while True:
            chunk = os.read(reader, min(1024 * 1024, len(data) - total + 1))
            if not chunk:
                break
            total += len(chunk)
            if total > len(data):
                raise CustodyError("memfd", "sealed candidate grew unexpectedly")
            digest.update(chunk)
        if total != len(data) or os.lseek(reader, 0, os.SEEK_CUR) != len(data) or digest.hexdigest() != hashlib.sha256(data).hexdigest():
            raise CustodyError("memfd", "sealed candidate bytes or hash differ")
        os.close(writer)
        writer = None
        diagnostic.close()
        return MaterializedIdentity(path=diagnostic.path, fd=reader, mode=info.st_mode, bytes=total, sha256=digest.hexdigest())
    except CustodyError:
        if reader is not None:
            os.close(reader)
        if writer is not None:
            os.close(writer)
        raise
    except OSError as error:
        if reader is not None:
            os.close(reader)
        if writer is not None:
            os.close(writer)
        raise CustodyError("memfd", f"cannot create sealed candidate: {error}") from error


def verify_and_materialize(record_or_raw: bytes | Mapping[str, Any], *, expected_manifest: bytes | Mapping[str, Any], expected_manifest_sha256: str | None = None, expected_manifest_hash: str | None = None, invocation_dir: Path, transfer_path: Path | None = None, now: Any | None = None) -> VerifiedCustody:
    """Verify custody and materialize candidate/receipt, without execution."""
    freeze_hash = _expected_hash(expected_manifest_sha256, expected_manifest_hash)
    validated = validate_custody_record(record_or_raw, expected_manifest=expected_manifest, expected_manifest_sha256=freeze_hash, now=now)
    transfer = validated["transfer"]
    locator = transfer["locator"]
    path = Path(locator["value"])
    if transfer_path is not None and Path(transfer_path) != path:
        raise CustodyError("locator", "caller transfer path differs from the custody locator")
    raw, _ = _checked_read(path, "transfer locator", MAX_ZIP_BYTES if transfer["kind"] == "github-actions-artifact-zip" else MAX_BUNDLE_BYTES)
    bundle = _zip_bundle(raw, transfer) if transfer["kind"] == "github-actions-artifact-zip" else raw
    members = _tar_members(bundle, transfer)
    _validate_sums(members["SHA256SUMS"], members)
    receipt_obj, metadata_obj = _validate_metadata(members, validated["role"], validated["source_commit"], validated["manifest"])
    receipt = validated["receipt"]
    candidate = validated["candidate"]
    if len(members["candidate"]) != candidate["bytes"] or hashlib.sha256(members["candidate"]).hexdigest() != candidate["sha256"]:
        raise CustodyError("candidate", "candidate bytes do not match custody identity")
    binary = receipt_obj["binary"]
    if binary["bytes"] != len(members["candidate"]) or binary["sha256"] != hashlib.sha256(members["candidate"]).hexdigest() or int(binary["mode"], 8) != 0o755:
        raise CustodyError("candidate", "candidate bytes do not match the build receipt binary observation")
    if len(members["build-receipt.json"]) != receipt["bytes"] or hashlib.sha256(members["build-receipt.json"]).hexdigest() != receipt["sha256"] or receipt_obj["receipt_sha256"] != receipt["self_hash"]:
        raise CustodyError("receipt", "receipt bytes do not match custody identity")
    directory_fd, _, invocation_root = _fresh_directory(Path(invocation_dir))
    candidate_identity: MaterializedIdentity | None = None
    receipt_identity: MaterializedIdentity | None = None
    try:
        candidate_identity = _materialize_file(directory_fd, Path(invocation_dir), "candidate", members["candidate"], 0o755, "candidate")
        candidate_identity = _sealed_candidate(members["candidate"], candidate_identity)
        receipt_identity = _materialize_file(directory_fd, Path(invocation_dir), "build-receipt.json", members["build-receipt.json"], 0o644, "build receipt")
        os.fsync(directory_fd)
        names = set(os.listdir(directory_fd))
        if names != {"candidate", "build-receipt.json"}:
            raise CustodyError("race", "invocation directory changed during materialization")
    except Exception:
        # Never unlink rollback output.  The invocation directory is fresh and
        # remains diagnostic debris on failure; descriptor ownership is the
        # only cleanup responsibility of this verifier.
        if candidate_identity is not None:
            candidate_identity.close()
        if receipt_identity is not None:
            receipt_identity.close()
        raise
    finally:
        os.close(directory_fd)
    assert candidate_identity is not None and receipt_identity is not None
    return VerifiedCustody(selector=validated["selector"], platform_role=validated["role"], source_commit=validated["source_commit"], successor_manifest_sha256=freeze_hash, candidate=candidate_identity, receipt=receipt_identity, transfer_kind=transfer["kind"])


# Names used by callers that prefer an explicit verb or a short validator.
verify_custody = verify_and_materialize
materialize_custody = verify_and_materialize
verify_custody_record = validate_custody_record


def main(argv: list[str] | None = None) -> int:
    raise SystemExit("This module is an execution-incapable library; use verify_and_materialize() from a caller")


if __name__ == "__main__":
    main()

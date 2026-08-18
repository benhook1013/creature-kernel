#!/usr/bin/env python3
"""Execution-incapable Gate B admission and human-authorization contracts.

The two records in this module are deliberately separate from candidate
execution.  A Gate B admission records that the current frozen package has
received the required clean Double review; it still has
``execution_permitted: false``.  A later authorization binds one attempt to
that admission and to one exact custody record.  Encoding an authorization is
only canonical record writing: it is not evidence that Ben approved it.

One-shot replay prevention is owned by the exact attempt wrapper's exclusive
prelaunch reservation.  This pure module can authenticate a one-attempt/no-
retry record, but it cannot persist or reserve state.  Likewise, distinct
reviewer identifiers and artifacts are checked here while reviewer-process
independence remains a trusted review-orchestration boundary.

The validator consumes exact bytes.  Freeze bytes are authenticated by the
canonical pure freeze validator, review files are read through an anchored
descriptor walk with no-follow checks, and no Git, process, candidate, or
network operation is performed here.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
from typing import Any, Mapping


PHASE_ID = "exp-0002-phase3-semantic-band-conformance-001"
EXPERIMENT_ID = "EXP-0002"
CANDIDATE_PROFILE_ID = "ck.provisional-r3-authored-conflict.semantic-band-1"

ADMISSION_SCHEMA = "ck.exp-0002.phase3.gate-b-admission-1"
AUTHORIZATION_SCHEMA = "ck.exp-0002.phase3.exact-attempt-human-authorization-1"
ADMISSION_HASH_DOMAIN = b"ck.exp-0002.phase3.gate-b-admission.v1\0"
AUTHORIZATION_HASH_DOMAIN = b"ck.exp-0002.phase3.exact-attempt-human-authorization.v1\0"
FREEZE_SCHEMA = "ck.exp-0002.phase3.freeze-manifest-2"

# These are the two independent lenses required for the final Gate B Double.
# They are intentionally a closed set so a pair of reviews cannot be made
# admissible merely by inventing two agreeable labels.
REQUIRED_REVIEW_LENSES = ("closure-and-custody", "execution-admissibility")
REQUIRED_EXACT_RUNTIME_TOOLS = (
    "scripts/phase3_exact_adjudicator.py",
    "scripts/phase3_exact_authority.py",
    "scripts/phase3_exact_custody.py",
    "scripts/phase3_exact_fp_observer.py",
    "scripts/phase3_exact_publication.py",
    "scripts/phase3_exact_transport.py",
    "scripts/phase3_exact_attempt.py",
)
PLATFORM_ORDINALS = {
    "wsl2-x86_64": frozenset({0, 1}),
    "ubuntu-24.04-x86_64": frozenset({2}),
}

MAX_RECORD_BYTES = 64 * 1024
MAX_REVIEW_BYTES = 256 * 1024
MAX_JSON_DEPTH = 24
MAX_STRING_BYTES = 4096
MAX_PATH_BYTES = 512
SHA_HEX = set("0123456789abcdef")
COMMIT_HEX = SHA_HEX


class AuthorityError(ValueError):
    """Stable fail-closed error from the authority boundary."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = str(code)
        self.detail = str(detail).replace("\x00", "?").replace("\n", " ").replace("\r", "")[:300]
        super().__init__(f"{self.code}: {self.detail}" if self.detail else self.code)


def _fail(code: str, detail: str = "") -> None:
    raise AuthorityError(code, detail)


def _canonical(value: Any) -> bytes:
    try:
        return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise AuthorityError("canonical-json", "value cannot be represented as canonical JSON") from error


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in items:
        if key in result:
            _fail("duplicate-json-key", key)
        result[key] = value
    return result


def _constant(token: str) -> None:
    _fail("nonfinite-json", token)


def _depth(value: Any, level: int = 0) -> None:
    if level > MAX_JSON_DEPTH:
        _fail("json-depth", "JSON exceeds the bounded nesting depth")
    if isinstance(value, dict):
        for key, child in value.items():
            if type(key) is not str:
                _fail("json-key", "JSON object key is not a string")
            _depth(child, level + 1)
    elif isinstance(value, list):
        for child in value:
            _depth(child, level + 1)


def _parse_record(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > MAX_RECORD_BYTES or not raw.endswith(b"\n"):
        _fail("record-size", f"{label} is absent, oversized, or missing its trailing newline")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_constant)
    except AuthorityError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as error:
        raise AuthorityError("malformed-json", f"{label} is not strict JSON") from error
    _depth(value)
    if type(value) is not dict:
        _fail("record-shape", f"{label} must be a JSON object")
    if _canonical(value) != raw:
        _fail("noncanonical", f"{label} is not canonical JSON")
    return value


def _exact_keys(value: Any, keys: set[str], label: str) -> None:
    if type(value) is not dict or set(value) != keys:
        _fail("schema", f"{label} has missing or unexpected fields")


def _string(value: Any, label: str, *, maximum: int = MAX_STRING_BYTES) -> str:
    if type(value) is not str or not value or "\x00" in value:
        _fail("field", f"{label} is not a non-empty string")
    try:
        size = len(value.encode("utf-8"))
    except UnicodeEncodeError as error:
        raise AuthorityError("field", f"{label} is not valid UTF-8") from error
    if size > maximum:
        _fail("field-size", f"{label} exceeds its byte bound")
    return value


def _sha(value: Any, label: str) -> str:
    result = _string(value, label, maximum=64)
    if len(result) != 64 or any(char not in SHA_HEX for char in result):
        _fail("digest", f"{label} is not a lowercase SHA-256 digest")
    return result


def _commit(value: Any, label: str) -> str:
    result = _string(value, label, maximum=40)
    if len(result) != 40 or any(char not in COMMIT_HEX for char in result):
        _fail("commit", f"{label} is not a lowercase full Git commit SHA")
    return result


def _bool(value: Any, label: str, expected: bool | None = None) -> bool:
    if type(value) is not bool or (expected is not None and value is not expected):
        _fail("field", f"{label} has the wrong boolean value")
    return value


def _bounded_int(value: Any, label: str, *, minimum: int = 0, maximum: int = 2**31 - 1) -> int:
    if type(value) is not int or isinstance(value, bool) or not minimum <= value <= maximum:
        _fail("field", f"{label} is outside its integer bound")
    return value


def _safe_relative(value: Any, label: str) -> str:
    result = _string(value, label, maximum=MAX_PATH_BYTES)
    if result.startswith("/") or "\\" in result:
        _fail("path", f"{label} is not a safe relative path")
    parts = result.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        _fail("path", f"{label} contains an unsafe component")
    if not result.endswith(".md"):
        _fail("path", f"{label} must identify a Markdown review")
    return result


def _freeze_module() -> Any:
    path = Path(__file__).with_name("phase3_freeze_manifest.py")
    spec = importlib.util.spec_from_file_location("phase3_exact_authority_freeze", path)
    if spec is None or spec.loader is None:
        _fail("freeze-validator", "canonical freeze validator cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as error:
        raise AuthorityError("freeze-validator", "canonical freeze validator cannot be loaded") from error
    return module


def validate_required_exact_runtime_tools(manifest: Mapping[str, Any]) -> dict[str, tuple[str, ...]]:
    """Validate the successor freeze's closed exact-runtime tool collection."""
    identities = manifest.get("exact_runtime_tool_identities") if isinstance(manifest, Mapping) else None
    if type(identities) is not list:
        _fail("runtime-tool-closure", "freeze exact_runtime_tool_identities is not a list")
    counts: dict[str, int] = {path: 0 for path in REQUIRED_EXACT_RUNTIME_TOOLS}
    for index, identity in enumerate(identities):
        if type(identity) is not dict:
            _fail("runtime-tool-closure", f"exact runtime tool identity {index} is not an object")
        path = identity.get("path")
        if path not in counts:
            _fail("runtime-tool-closure", f"freeze contains an unexpected exact runtime tool: {path}")
        counts[path] += 1
        if counts[path] != 1:
            _fail("runtime-tool-closure", f"required exact runtime tool is duplicated: {path}")
        _exact_keys(identity, {"path", "mode", "bytes", "sha256"}, f"runtime tool {path}")
        if type(identity["mode"]) is not int or identity["mode"] != 0o644:
            _fail("runtime-tool-closure", f"required exact runtime tool mode is not 0644: {path}")
        _bounded_int(identity["bytes"], f"runtime tool {path}.bytes", minimum=1, maximum=16 * 1024 * 1024)
        _sha(identity["sha256"], f"runtime tool {path}.sha256")
    present = tuple(path for path in REQUIRED_EXACT_RUNTIME_TOOLS if counts[path] == 1)
    missing = tuple(path for path in REQUIRED_EXACT_RUNTIME_TOOLS if counts[path] == 0)
    if missing:
        _fail("runtime-tool-closure", "successor freeze omits required exact runtime tools: " + ", ".join(missing))
    if tuple(identity["path"] for identity in identities) != REQUIRED_EXACT_RUNTIME_TOOLS:
        _fail("runtime-tool-closure", "freeze exact runtime tools are not in canonical order")
    return {"present": present, "missing": missing}


def _validate_freeze(raw: bytes) -> tuple[dict[str, Any], str]:
    if type(raw) is not bytes:
        _fail("freeze", "freeze manifest must be supplied as exact bytes")
    try:
        freeze = _freeze_module()
        value = freeze.validate_manifest(raw)
    except Exception as error:
        raise AuthorityError("freeze", f"canonical freeze validator rejected bytes: {error}") from error
    if value.get("schema") != FREEZE_SCHEMA:
        _fail("freeze-version", "exact authority requires the successor freeze-manifest-2 contract")
    validate_required_exact_runtime_tools(value)
    _commit(value.get("execution_tool_source_commit"), "manifest.execution_tool_source_commit")
    try:
        checked = freeze.check_manifest()
    except Exception as error:
        raise AuthorityError(
            "freeze-current",
            f"repository-bound current freeze check failed: {error}",
        ) from error
    if (
        type(checked) is not dict
        or checked != value
        or checked.get("manifest_sha256") != value.get("manifest_sha256")
        or _canonical(checked) != raw
    ):
        _fail(
            "freeze-current",
            "repository-bound current freeze differs from the exact supplied manifest",
        )
    # The bound freeze identity is the manifest's authenticated domain-framed
    # self-hash, matching custody records. Pure validation alone is deliberately
    # insufficient for authority: check_manifest additionally proves the C-to-E
    # ancestry and current committed execution-tool snapshot owned by the
    # canonical freeze module.
    return value, value["manifest_sha256"]


def _open_root(root: Path) -> int:
    if not isinstance(root, Path):
        root = Path(root)
    if not root.is_absolute() or any(part in {"", ".", ".."} for part in root.parts[1:]):
        _fail("review-root", "review root must be an absolute normalized path")
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    fd = -1
    try:
        fd = os.open(os.sep, flags)
        for part in root.parts[1:]:
            child = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = child
        info = os.fstat(fd)
        if not stat.S_ISDIR(info.st_mode):
            _fail("review-root", "review root is not a directory")
        return fd
    except AuthorityError:
        if fd >= 0:
            os.close(fd)
        raise
    except OSError as error:
        if fd >= 0:
            os.close(fd)
        raise AuthorityError("review-root", f"cannot open anchored review root: {error}") from error


def _read_review(root_fd: int, relative: str) -> tuple[bytes, int, str]:
    parts = relative.split("/")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NONBLOCK", 0)
    fd = -1
    opened_dirs: list[int] = []
    try:
        parent = root_fd
        for part in parts[:-1]:
            next_fd = os.open(part, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0), dir_fd=parent)
            opened_dirs.append(next_fd)
            parent = next_fd
        fd = os.open(parts[-1], flags, dir_fd=parent)
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            _fail("review-file", f"{relative} is not a single-link regular file")
        if before.st_size <= 0 or before.st_size > MAX_REVIEW_BYTES:
            _fail("review-file-size", f"{relative} exceeds the review bound")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(fd, min(64 * 1024, MAX_REVIEW_BYTES + 1 - total))
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_REVIEW_BYTES:
                _fail("review-file-size", f"{relative} exceeds the review bound")
            chunks.append(chunk)
        after = os.fstat(fd)
        before_meta = (before.st_dev, before.st_ino, before.st_mode, before.st_nlink, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
        after_meta = (after.st_dev, after.st_ino, after.st_mode, after.st_nlink, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
        if before_meta != after_meta or total != before.st_size:
            _fail("review-race", f"{relative} changed while being read")
        # Keep the anchored parent descriptor open through this final lstat-
        # by-name comparison.  The opened descriptor alone would otherwise
        # continue to validate after its directory entry had been replaced.
        path_after = os.stat(parts[-1], dir_fd=parent, follow_symlinks=False)
        path_meta = (path_after.st_dev, path_after.st_ino, path_after.st_mode, path_after.st_nlink, path_after.st_size, path_after.st_mtime_ns, path_after.st_ctime_ns)
        if path_meta != after_meta:
            _fail("review-race", f"{relative} path identity changed while being read")
        raw = b"".join(chunks)
        return raw, total, hashlib.sha256(raw).hexdigest()
    except AuthorityError:
        raise
    except OSError as error:
        raise AuthorityError("review-file", f"cannot read {relative}: {error}") from error
    finally:
        if fd >= 0:
            os.close(fd)
        for child in reversed(opened_dirs):
            os.close(child)


def _review_shape(review: Any, index: int) -> dict[str, Any]:
    label = f"reviews[{index}]"
    _exact_keys(review, {"review_id", "reviewer", "lens", "path", "bytes", "sha256", "status", "disposition", "findings"}, label)
    review_id = _string(review["review_id"], f"{label}.review_id")
    reviewer = _string(review["reviewer"], f"{label}.reviewer")
    lens = _string(review["lens"], f"{label}.lens")
    path = _safe_relative(review["path"], f"{label}.path")
    size = _bounded_int(review["bytes"], f"{label}.bytes", minimum=1, maximum=MAX_REVIEW_BYTES)
    digest = _sha(review["sha256"], f"{label}.sha256")
    if review["status"] != "passed" or review["disposition"] != "Clean":
        _fail("review-status", f"{label} is not a passed Clean review")
    if type(review["findings"]) is not list or review["findings"] != []:
        _fail("review-findings", f"{label} does not record no findings")
    return {"review_id": review_id, "reviewer": reviewer, "lens": lens, "path": path, "bytes": size, "sha256": digest, "status": "passed", "disposition": "Clean", "findings": []}


ADMISSION_KEYS = {"schema", "experiment_id", "phase_id", "candidate_profile_id", "freeze_manifest_sha256", "execution_tool_source_commit", "reviewed_commit", "reviews", "status", "execution_permitted", "admission_record_sha256"}


def _admission_shape(value: Mapping[str, Any]) -> dict[str, Any]:
    _exact_keys(value, ADMISSION_KEYS, "admission record")
    if value["schema"] != ADMISSION_SCHEMA or value["experiment_id"] != EXPERIMENT_ID or value["phase_id"] != PHASE_ID or value["candidate_profile_id"] != CANDIDATE_PROFILE_ID:
        _fail("admission-binding", "admission fixed identity is wrong")
    freeze_hash = _sha(value["freeze_manifest_sha256"], "admission.freeze_manifest_sha256")
    source = _commit(value["execution_tool_source_commit"], "admission.execution_tool_source_commit")
    reviewed = _commit(value["reviewed_commit"], "admission.reviewed_commit")
    if source != reviewed:
        _fail("reviewed-commit", "reviewed commit differs from execution-tool source commit")
    if value["status"] != "passed" or value["execution_permitted"] is not False:
        _fail("admission-status", "admission is not passed and execution-disabled")
    reviews = value["reviews"]
    if type(reviews) is not list or len(reviews) != 2:
        _fail("review-count", "Gate B admission requires exactly two reviews")
    normalized = [_review_shape(review, index) for index, review in enumerate(reviews)]
    if {item["lens"] for item in normalized} != set(REQUIRED_REVIEW_LENSES):
        _fail("review-lenses", "reviews do not contain the two required distinct lenses")
    for field in ("review_id", "reviewer", "path", "lens"):
        if len({item[field] for item in normalized}) != 2:
            _fail("review-identity", f"reviews duplicate {field}")
    return {**dict(value), "freeze_manifest_sha256": freeze_hash, "execution_tool_source_commit": source, "reviewed_commit": reviewed, "reviews": normalized}


def _check_self_hash(value: Mapping[str, Any], field: str, domain: bytes, label: str) -> None:
    supplied = _sha(value.get(field), f"{label}.{field}")
    unsigned = dict(value)
    unsigned[field] = None
    if hashlib.sha256(domain + _canonical(unsigned)[:-1]).hexdigest() != supplied:
        _fail("record-hash", f"{label} self-hash does not match canonical contents")


def encode_gate_b_admission(record: Mapping[str, Any]) -> bytes:
    """Write a canonical, self-hashed admission record without filesystem proof."""
    value = dict(record)
    value["admission_record_sha256"] = None
    _admission_shape(value)
    unsigned = _canonical(value)
    value["admission_record_sha256"] = hashlib.sha256(ADMISSION_HASH_DOMAIN + unsigned[:-1]).hexdigest()
    return _canonical(value)


def validate_gate_b_admission(raw: bytes, *, freeze_manifest: bytes, review_root: Path | str) -> dict[str, Any]:
    """Validate an admission against exact freeze bytes and anchored reviews."""
    value = _parse_record(raw, "admission record")
    normalized = _admission_shape(value)
    manifest, manifest_hash = _validate_freeze(freeze_manifest)
    if manifest_hash != normalized["freeze_manifest_sha256"]:
        _fail("freeze-binding", "admission freeze hash differs from exact manifest bytes")
    binding = manifest["binding"]
    if normalized["experiment_id"] != binding["experiment_id"] or normalized["phase_id"] != binding["phase_id"] or normalized["candidate_profile_id"] != binding["candidate_profile_id"]:
        _fail("freeze-binding", "admission identity differs from frozen binding")
    execution_source = manifest["execution_tool_source_commit"]
    if normalized["execution_tool_source_commit"] != execution_source or normalized["reviewed_commit"] != execution_source:
        _fail("source-binding", "admission commit does not equal frozen execution-tool source commit")
    binaries = manifest.get("binaries")
    readiness = manifest.get("readiness")
    if (
        type(binaries) is not dict
        or set(binaries) != set(PLATFORM_ORDINALS)
        or any(type(slot) is not dict or slot.get("status") != "bound" for slot in binaries.values())
        or type(readiness) is not dict
        or readiness.get("materialization_state") != "frozen"
        or readiness.get("freeze_blockers") != []
        or readiness.get("execution_permitted") is not False
        or manifest.get("execution_permitted") is not False
    ):
        _fail("freeze-readiness", "Gate B admission requires a fully bound, blocker-free, execution-disabled frozen manifest")
    root_fd = _open_root(Path(review_root))
    try:
        for review in normalized["reviews"]:
            raw_review, size, digest = _read_review(root_fd, review["path"])
            if size != review["bytes"] or digest != review["sha256"]:
                _fail("review-identity", f"review bytes or hash differ for {review['path']}")
            del raw_review
    finally:
        os.close(root_fd)
    _check_self_hash(normalized, "admission_record_sha256", ADMISSION_HASH_DOMAIN, "admission record")
    return normalized


AUTHORIZATION_KEYS = {"schema", "experiment_id", "phase_id", "candidate_profile_id", "admission_record_sha256", "freeze_manifest_sha256", "custody_record_sha256", "attempt_id", "platform_selector", "ordinal", "authorization_reference", "scope", "execution_permitted", "automatic_retry", "authorization_record_sha256"}


def _valid_attempt_id(value: Any) -> str:
    result = _string(value, "authorization.attempt_id", maximum=128)
    if not result.startswith("attempt-") or len(result) < 11 or any(char not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-" for char in result):
        _fail("attempt-id", "authorization attempt_id is not a canonical attempt identifier")
    return result


def _authorization_shape(value: Mapping[str, Any]) -> dict[str, Any]:
    _exact_keys(value, AUTHORIZATION_KEYS, "authorization record")
    if value["schema"] != AUTHORIZATION_SCHEMA or value["experiment_id"] != EXPERIMENT_ID or value["phase_id"] != PHASE_ID or value["candidate_profile_id"] != CANDIDATE_PROFILE_ID:
        _fail("authorization-binding", "authorization fixed identity is wrong")
    admission_hash = _sha(value["admission_record_sha256"], "authorization.admission_record_sha256")
    freeze_hash = _sha(value["freeze_manifest_sha256"], "authorization.freeze_manifest_sha256")
    custody_hash = _sha(value["custody_record_sha256"], "authorization.custody_record_sha256")
    attempt_id = _valid_attempt_id(value["attempt_id"])
    selector = _string(value["platform_selector"], "authorization.platform_selector", maximum=64)
    if selector not in PLATFORM_ORDINALS:
        _fail("platform", "authorization platform selector is not canonical")
    ordinal = _bounded_int(value["ordinal"], "authorization.ordinal", maximum=2)
    if ordinal not in PLATFORM_ORDINALS[selector]:
        _fail("ordinal", "authorization ordinal is not allowed for the selected platform")
    reference = _string(value["authorization_reference"], "authorization.authorization_reference", maximum=1024)
    folded = reference.casefold().strip()
    if folded in {"tbd", "todo", "pending", "placeholder", "none", "null", "n/a", "na"} or (folded.startswith("<") and folded.endswith(">")):
        _fail("authorization-reference", "authorization reference is a placeholder")
    if value["scope"] != "exact-attempt" or value["execution_permitted"] is not True or value["automatic_retry"] is not False:
        _fail("authorization-policy", "authorization is not the fixed one-attempt policy")
    return {**dict(value), "admission_record_sha256": admission_hash, "freeze_manifest_sha256": freeze_hash, "custody_record_sha256": custody_hash, "attempt_id": attempt_id, "platform_selector": selector, "ordinal": ordinal, "authorization_reference": reference}


def encode_authorization(record: Mapping[str, Any]) -> bytes:
    """Write a canonical authorization; this does not prove human approval."""
    value = dict(record)
    value["authorization_record_sha256"] = None
    _authorization_shape(value)
    unsigned = _canonical(value)
    value["authorization_record_sha256"] = hashlib.sha256(AUTHORIZATION_HASH_DOMAIN + unsigned[:-1]).hexdigest()
    return _canonical(value)


def validate_authorization(raw: bytes, *, admission_bytes: bytes, freeze_manifest: bytes, review_root: Path | str, expected_custody_record_sha256: str, expected_attempt_id: str, expected_platform_selector: str, expected_ordinal: int, expected_authorization_reference: str) -> dict[str, Any]:
    """Validate one authorization and its exact, fully reviewed admission.

    The caller must supply the exact expected human-authorization reference.
    Exclusive prelaunch reservation by the exact-attempt layer separately owns
    one-shot replay prevention; this execution-incapable validator has no
    persistent state.
    """
    admission = validate_gate_b_admission(admission_bytes, freeze_manifest=freeze_manifest, review_root=review_root)
    admission_hash = hashlib.sha256(admission_bytes).hexdigest()
    value = _parse_record(raw, "authorization record")
    normalized = _authorization_shape(value)
    if normalized["admission_record_sha256"] != admission_hash:
        _fail("admission-binding", "authorization does not bind exact admission bytes")
    if normalized["freeze_manifest_sha256"] != admission["freeze_manifest_sha256"]:
        _fail("freeze-binding", "authorization does not bind admission freeze")
    expected_custody = _sha(expected_custody_record_sha256, "expected custody record SHA")
    if normalized["custody_record_sha256"] != expected_custody:
        _fail("custody-binding", "authorization custody record differs from expected custody")
    if normalized["attempt_id"] != _valid_attempt_id(expected_attempt_id):
        _fail("attempt-binding", "authorization attempt differs from expected attempt")
    expected_selector = _string(expected_platform_selector, "expected platform selector", maximum=64)
    if normalized["platform_selector"] != expected_selector:
        _fail("platform-binding", "authorization platform differs from expected platform")
    if normalized["ordinal"] != _bounded_int(expected_ordinal, "expected ordinal", maximum=2):
        _fail("ordinal-binding", "authorization ordinal differs from expected ordinal")
    if normalized["authorization_reference"] != _string(expected_authorization_reference, "expected authorization reference", maximum=1024):
        _fail("authorization-reference", "authorization reference differs from expected reference")
    _check_self_hash(normalized, "authorization_record_sha256", AUTHORIZATION_HASH_DOMAIN, "authorization record")
    return normalized


# Explicit aliases make the contract discoverable to callers using either the
# record name or the boundary name.  They do not add alternate semantics.
encode_admission_record = encode_gate_b_admission
validate_admission_record = validate_gate_b_admission
encode_human_authorization = encode_authorization
validate_human_authorization = validate_authorization


def main(argv: list[str] | None = None) -> int:
    raise SystemExit("This module is an execution-incapable library; use its validators from a caller")


__all__ = [
    "ADMISSION_SCHEMA", "AUTHORIZATION_SCHEMA", "FREEZE_SCHEMA", "REQUIRED_REVIEW_LENSES", "REQUIRED_EXACT_RUNTIME_TOOLS", "PLATFORM_ORDINALS",
    "validate_required_exact_runtime_tools",
    "AuthorityError", "encode_gate_b_admission", "validate_gate_b_admission", "encode_authorization", "validate_authorization",
    "encode_admission_record", "validate_admission_record", "encode_human_authorization", "validate_human_authorization",
]


if __name__ == "__main__":
    main()

"""Read-only adapter for the materialized Phase 3 request package.

The materialization is a package input, not an execution command.  This module
checks the package's existing manifests and generated request partitions, then
projects each request into the deliberately closed in-memory case shape used by
``phase3_runner.run_synthetic``.  Recipe construction and expected outcome
metadata never cross that projection boundary; in particular, held-out cases
are opaque to callers of :func:`load_materialized_cases`.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from decimal import Decimal
from pathlib import Path
import stat
from typing import Any, Mapping

import phase3_oracle as oracle
import phase3_runner as runner
from phase3_common import (
    FRAME_BYTES,
    MAX_REQUEST_ID_BYTES,
    MAX_SOURCE_BYTES,
    Phase3Error,
    bounded_decimal,
    bits_to_float,
    canonical_json,
    float_to_bits,
)


# The package is intentionally below these bounds today.  The limits are
# package-level bounds, in addition to the per-line/per-source limits inherited
# from the Phase 2 request contract.
MAX_PACKAGE_BYTES = 8 * 1024 * 1024
MAX_MANIFEST_BYTES = 2 * 1024 * 1024
MAX_PARTITION_BYTES = 2 * 1024 * 1024
MAX_SQRT_BYTES = FRAME_BYTES
MAX_PREREG_BYTES = 2 * 1024 * 1024
MAX_GENERATOR_BYTES = 512 * 1024
MAX_INTEGER_TOKEN_BYTES = 256
MAX_INTEGER_BITS = 640
EXPECTED_TOTAL_RECORDS = 60
PREREGISTRATION_PATH = "preregistration.json"
GENERATOR_PATH = "scripts/generate_phase3.py"
EXPECTED_FIXTURE_PATH = "examples/body-documents/stylized-digitigrade-biped.json"
EXPECTED_FIXTURE_SHA256 = "49937955d25538bc9546689427022ce71776192834ec829b8dc005bb4518a66f"
EXTRA_REQUEST_ID_PREFIX = "adapter-extra/"

PACKAGE_FILES = frozenset({
    "corpora/development.jsonl",
    "corpora/held-out.jsonl",
    "corpora/controls.jsonl",
    "manifests/recipe-manifest.json",
    "manifests/artifact-manifest.json",
    "sqrt-vectors.json",
})
FREEZE_MANIFEST_PATH = "freeze-manifest.json"
FREEZE_RECEIPT_DIRECTORY = "build-receipts"
FREEZE_RECEIPT_NAMES = frozenset({"wsl.json", "native.json"})
PARTITIONS = (
    ("development", "corpora/development.jsonl", 8),
    ("held-out", "corpora/held-out.jsonl", 40),
    ("controls", "corpora/controls.jsonl", 12),
)
EXPECTED_PROTOCOL = "ck.exp-0002.r3-authored-conflict-candidate-request-1"
EXPECTED_OPERATION = "observe-authored-conflict"
EXPECTED_RESOURCE_PROFILE = "ordinary"
EXPECTED_PROVIDERS = {
    "gate": "allow",
    "arithmetic": "native",
    "sqrt": "native",
    "environment": "unattested-no-probe-v1",
}
EXPECTED_REQUEST_ID_FORMULA = "p3-{attempt_id}-{global_ordinal:03d}"
EXPECTED_TRANSLATION_BITS = "0x3f0a36e2eb1c432d"
EXPECTED_HALF_CHORD_BITS = "0x3ec4f8b588e368f1"
EXPECTED_FULL_CHORD_BITS = "0x3ed4f8b588e368f1"
EXPECTED_FAMILIES = (
    "identity-axis",
    "non-identity-rigid",
    "basis-unit-conversion",
    "composed-rigid-chain",
    "conditioning-safe-mixed",
)
EXPECTED_HELD_OUT_STRATA = {
    "agree": ("0.50T", "0.85T"),
    "conflict": ("1.05-certain", "1.05-gross"),
}
EXPECTED_DEVELOPMENT_IDS = (
    "phase3/development/threshold-translation",
    "phase3/development/near-threshold-rotation",
    "phase3/development/sign-equivalence",
    "phase3/development/conversion",
    "phase3/development/four-edge",
    "phase3/development/attachment-equation",
    "phase3/development/identity-zero-zero",
    "phase3/development/conditioning-near-limit",
)
EXPECTED_CONTROL_IDS = (
    "phase3/control/gray-translation-1.05T",
    "phase3/control/gray-translation-material",
    "phase3/control/gray-rotation-1.05T",
    "phase3/control/gray-rotation-material",
    "phase3/control/admit-zero-authored",
    "phase3/control/admit-zero-host",
    "phase3/control/admit-zero-offset",
    "phase3/control/admit-zero-mating",
    "phase3/control/domain-component",
    "phase3/control/domain-path",
    "phase3/control/domain-conditioning-above-limit",
    "phase3/control/numeric-negative-relative",
)
CASE_KEYS = frozenset({
    "assignment", "case_id", "condition_expectation", "construction",
    "construction_target", "dispatch_to_candidate", "domain_expectation",
    "expected_class", "family", "global_ordinal", "metric", "source_bytes",
    "source_sha256", "source_truth", "stratum", "typed_expectation",
})
REQUEST_KEYS = frozenset({
    "operation", "protocol_id", "providers", "request_id", "resource_profile",
    "source", "tolerances",
})
TOLERANCE_KEYS = frozenset({
    "translation_absolute", "translation_relative", "rotation_half_chord",
})
PROVIDER_KEYS = frozenset(EXPECTED_PROVIDERS)


class MaterializedAdapterError(Phase3Error):
    """A stable, bounded materialized-package preflight error."""


def _fail(code: str, detail: str) -> None:
    raise MaterializedAdapterError(code, detail)


def _expect(condition: bool, code: str, detail: str) -> None:
    if not condition:
        _fail(code, detail)


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in items:
        if key in result:
            _fail("duplicate-json-member", f"duplicate JSON member {key}")
        result[key] = value
    return result


def _constant(value: str) -> None:
    _fail("nonfinite-json", f"non-finite JSON constant {value}")


def _decimal(value: str) -> Any:
    try:
        return bounded_decimal(value)
    except Phase3Error as error:
        raise MaterializedAdapterError(error.code, error.detail) from error


def _integer(value: str) -> int:
    if len(value) > MAX_INTEGER_TOKEN_BYTES:
        _fail("numeric-significand-too-large", "integer token exceeds 256 bytes")
    try:
        result = int(value)
    except ValueError as error:
        raise MaterializedAdapterError("numeric-token", "integer token is invalid") from error
    if result.bit_length() > MAX_INTEGER_BITS:
        _fail("numeric-significand-too-large", "integer token exceeds the bounded integer width")
    return result


def _float(value: str) -> float:
    decimal = _decimal(value)
    try:
        result = float(decimal)
    except (OverflowError, ValueError) as error:
        raise MaterializedAdapterError("numeric-token", "floating token is invalid") from error
    _expect(math.isfinite(result), "nonfinite-json", "floating token is non-finite")
    return result


def _parse_json(raw: bytes, label: str, limit: int, *, response_numbers: bool = False) -> Any:
    _expect(len(raw) <= limit, "resource-limit", f"{label} exceeds {limit} bytes")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise MaterializedAdapterError("invalid-utf8", f"{label} is not UTF-8") from error
    _expect(not text.startswith("\ufeff"), "utf8-bom", f"{label} has a UTF-8 BOM")
    try:
        return json.loads(
            text,
            object_pairs_hook=_pairs,
            parse_int=_integer,
            parse_float=_float if response_numbers else _decimal,
            parse_constant=_constant,
        )
    except MaterializedAdapterError:
        raise
    except (json.JSONDecodeError, RecursionError, TypeError, ValueError) as error:
        raise MaterializedAdapterError("malformed-json", f"{label} is malformed") from error


def _absolute_path(value: str | os.PathLike[str]) -> Path:
    raw = Path(value)
    if not raw.is_absolute():
        raw = Path.cwd() / raw
    return Path(os.path.normpath(str(raw)))


def _reject_symlink_components(path: Path, label: str) -> None:
    # Do not resolve first: resolving would make a symlink indistinguishable
    # from the requested package root.  Existing ancestors are checked too.
    for component in reversed(path.parents):
        try:
            if component.is_symlink():
                _fail("symlink", f"{label} contains symlink component {component}")
        except OSError as error:
            raise MaterializedAdapterError("package-io", f"cannot inspect {component}") from error
    try:
        if path.is_symlink():
            _fail("symlink", f"{label} is a symlink")
    except OSError as error:
        raise MaterializedAdapterError("package-io", f"cannot inspect {path}") from error


def _lstat(path: Path, label: str) -> os.stat_result:
    _reject_symlink_components(path, label)
    try:
        return path.lstat()
    except FileNotFoundError as error:
        raise MaterializedAdapterError("missing-path", f"{label} is missing") from error
    except OSError as error:
        raise MaterializedAdapterError("package-io", f"cannot inspect {label}") from error


def _regular_bytes(path: Path, label: str, limit: int, expected_size: int | None = None) -> bytes:
    info = _lstat(path, label)
    _expect(stat.S_ISREG(info.st_mode), "non-regular-file", f"{label} is not a regular file")
    _expect(stat.S_IMODE(info.st_mode) == 0o644, "file-mode", f"{label} is not mode 0644")
    _expect(info.st_nlink == 1, "hardlink", f"{label} has multiple hard links")
    _expect(info.st_size <= limit, "resource-limit", f"{label} exceeds {limit} bytes")
    if expected_size is not None:
        _expect(info.st_size == expected_size, "artifact-size", f"{label} size differs from manifest")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        if error.errno in {getattr(os, "ELOOP", 40), 40}:
            raise MaterializedAdapterError("symlink", f"{label} is a symlink") from error
        raise MaterializedAdapterError("package-io", f"cannot open {label}") from error
    try:
        opened = os.fstat(descriptor)
        _expect(stat.S_ISREG(opened.st_mode), "non-regular-file", f"{label} is not a regular file")
        _expect(stat.S_IMODE(opened.st_mode) == 0o644, "file-mode", f"{label} changed mode")
        _expect(opened.st_nlink == 1, "hardlink", f"{label} changed link count")
        _expect((opened.st_dev, opened.st_ino, opened.st_size, opened.st_mode) == (info.st_dev, info.st_ino, info.st_size, info.st_mode), "file-race", f"{label} changed before read")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(1024 * 1024, limit + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            _expect(total <= limit, "resource-limit", f"{label} grew beyond {limit} bytes")
        raw = b"".join(chunks)
        after = os.fstat(descriptor)
    except OSError as error:
        raise MaterializedAdapterError("package-io", f"cannot read {label}") from error
    finally:
        os.close(descriptor)
    _expect((after.st_dev, after.st_ino, after.st_size, after.st_mode, after.st_nlink) == (info.st_dev, info.st_ino, len(raw), info.st_mode, 1), "file-race", f"{label} changed during read")
    try:
        current = path.lstat()
    except OSError as error:
        raise MaterializedAdapterError("file-race", f"cannot recheck {label}") from error
    _expect((current.st_dev, current.st_ino, current.st_size, current.st_mode, current.st_nlink) == (info.st_dev, info.st_ino, len(raw), info.st_mode, 1), "file-race", f"{label} changed after read")
    _expect(len(raw) <= limit, "resource-limit", f"{label} grew beyond {limit} bytes")
    if expected_size is not None:
        _expect(len(raw) == expected_size, "artifact-size", f"{label} size differs from manifest")
    return raw


def _directory(path: Path, label: str) -> None:
    info = _lstat(path, label)
    _expect(stat.S_ISDIR(info.st_mode), "package-layout", f"{label} is not a directory")


def _safe_relative(path: Any, label: str) -> str:
    _expect(isinstance(path, str) and path in PACKAGE_FILES, "artifact-path", f"{label} is not an expected package path")
    _expect("\\" not in path and not path.startswith("/") and ".." not in Path(path).parts, "artifact-path", f"{label} is not a safe relative path")
    return path


def _hex_sha(value: Any, label: str) -> str:
    _expect(isinstance(value, str) and len(value) == 64, "artifact-hash", f"{label} is not a SHA-256 string")
    _expect(all(char in "0123456789abcdef" for char in value), "artifact-hash", f"{label} is not lowercase hexadecimal")
    return value


def _expect_keys(value: Any, required: set[str] | frozenset[str], label: str) -> dict[str, Any]:
    _expect(type(value) is dict, "manifest-shape", f"{label} must be an object")
    _expect(set(value) == set(required), "manifest-shape", f"{label} has unexpected or missing members")
    return value


def _check_layout(root: Path) -> None:
    _directory(root, "package root")
    _directory(root / "corpora", "corpora directory")
    _directory(root / "manifests", "manifests directory")
    _directory(root / "scripts", "scripts directory")
    try:
        root_items = list(root.iterdir())
        corpus_items = list((root / "corpora").iterdir())
        manifest_items = list((root / "manifests").iterdir())
        for item in (*root_items, *corpus_items, *manifest_items):
            if item.is_symlink():
                _fail("symlink", f"package layout contains symlink {item}")
        root_entries = {entry.name for entry in root_items}
        corpus_entries = {entry.name for entry in corpus_items}
        manifest_entries = {entry.name for entry in manifest_items}
    except OSError as error:
        raise MaterializedAdapterError("package-io", "cannot inspect package layout") from error
    # The caller supplies the existing Phase 3 package root, which also owns
    # README/preregistration/review/script material.  Only the materialized
    # artifact subtrees are closed here; unrelated package documentation is not
    # an input to this adapter.
    _expect({"corpora", "manifests", "sqrt-vectors.json", PREREGISTRATION_PATH} <= root_entries, "package-layout", "package is missing expected materialized entries")
    _expect(corpus_entries == {"development.jsonl", "held-out.jsonl", "controls.jsonl"}, "package-layout", "package has unexpected corpus entries")
    _expect(
        manifest_entries <= {"recipe-manifest.json", "artifact-manifest.json", FREEZE_MANIFEST_PATH, FREEZE_RECEIPT_DIRECTORY},
        "package-layout",
        "package has unexpected manifest entries",
    )
    _expect(
        {"recipe-manifest.json", "artifact-manifest.json"} <= manifest_entries,
        "package-layout",
        "package is missing expected manifest entries",
    )
    # Gate B provenance is deliberately an optional sidecar to the generated
    # materialization.  Do not include it in PACKAGE_FILES or parse it here:
    # the adapter consumes only the generated request package and must remain
    # usable before the freeze sidecars exist.  If the sidecars are present,
    # keep their layout closed and apply the same basic file-safety checks as
    # package inputs without treating their contents as candidate data.
    if FREEZE_MANIFEST_PATH in manifest_entries:
        _regular_bytes(root / "manifests" / FREEZE_MANIFEST_PATH, "freeze manifest sidecar", MAX_MANIFEST_BYTES)
    if FREEZE_RECEIPT_DIRECTORY in manifest_entries:
        receipt_directory = root / "manifests" / FREEZE_RECEIPT_DIRECTORY
        _directory(receipt_directory, "freeze receipt directory")
        try:
            receipt_items = list(receipt_directory.iterdir())
            for item in receipt_items:
                if item.is_symlink():
                    _fail("symlink", f"package layout contains symlink {item}")
            receipt_entries = {entry.name for entry in receipt_items}
        except OSError as error:
            raise MaterializedAdapterError("package-io", "cannot inspect freeze receipt directory") from error
        _expect(receipt_entries <= FREEZE_RECEIPT_NAMES, "package-layout", "package has unexpected freeze receipt entries")
        for name in receipt_entries:
            _regular_bytes(receipt_directory / name, f"freeze receipt sidecar {name}", MAX_MANIFEST_BYTES)
    for relative in PACKAGE_FILES:
        _lstat(root / relative, relative)
    _lstat(root / PREREGISTRATION_PATH, PREREGISTRATION_PATH)
    _lstat(root / GENERATOR_PATH, GENERATOR_PATH)


def _identity_decl(value: Any, label: str, expected_path: str, *, allow_extra: bool = False) -> dict[str, Any]:
    if allow_extra:
        _expect(type(value) is dict and {"path", "bytes", "sha256"} <= set(value), "manifest-shape", f"{label} has missing identity members")
        obj = value
    else:
        obj = _expect_keys(value, {"path", "bytes", "sha256"}, label)
    _expect(obj["path"] == expected_path, "prereg-binding", f"{label} path differs")
    _expect(type(obj["bytes"]) is int and 0 <= obj["bytes"] <= MAX_PACKAGE_BYTES, "prereg-binding", f"{label} byte count is invalid")
    return {"path": expected_path, "bytes": obj["bytes"], "sha256": _hex_sha(obj["sha256"], f"{label}.sha256")}


def _validate_typed_expectation(value: Any, label: str, *, rejection: bool) -> None:
    expected_keys = {"cause", "error", "status"} if rejection else {"cause", "classification", "status"}
    item = _expect_keys(value, expected_keys, label)
    if rejection:
        _expect(item["status"] == "rejected" and isinstance(item["error"], str), "recipe-control", f"{label} rejection shape is invalid")
        cause = _expect_keys(item["cause"], {"code", "failure", "field"}, f"{label}.cause")
        _expect(all(isinstance(cause[key], str) and cause[key] for key in ("code", "failure", "field")), "recipe-control", f"{label}.cause fields are invalid")
        return
    _expect(item["status"] == "observed" and item["classification"] == "skipped", "recipe-control", f"{label} typed shape is invalid")
    cause = _expect_keys(item["cause"], {"code", "failure", "location"}, f"{label}.cause")
    _expect(isinstance(cause["code"], str) and isinstance(cause["failure"], str), "recipe-control", f"{label}.cause code is invalid")
    location = _expect_keys(cause["location"], {"member", "role", "slot"}, f"{label}.cause.location")
    member = _expect_keys(location["member"], {"document", "namespace"}, f"{label}.cause.location.member")
    _expect(all(isinstance(member[key], str) and member[key] for key in ("document", "namespace")), "recipe-control", f"{label}.cause member is invalid")
    _expect(isinstance(location["role"], str) and location["role"], "recipe-control", f"{label}.cause role is invalid")
    slot = _expect_keys(location["slot"], {"address", "component", "kind"}, f"{label}.cause.location.slot")
    _expect(isinstance(slot["component"], str) and isinstance(slot["kind"], str), "recipe-control", f"{label}.cause slot is invalid")
    address = _expect_keys(slot["address"], {"anchors", "kind", "namespace", "role"}, f"{label}.cause.location.slot.address")
    _expect(isinstance(address["anchors"], list) and all(isinstance(anchor, str) for anchor in address["anchors"]), "recipe-control", f"{label}.cause address anchors are invalid")
    _expect(all(isinstance(address[key], str) and address[key] for key in ("kind", "namespace", "role")), "recipe-control", f"{label}.cause address is invalid")


def _validate_preregistration(raw: bytes) -> dict[str, dict[str, Any]]:
    prereg = _parse_json(raw, "preregistration", MAX_PREREG_BYTES)
    _expect(type(prereg) is dict, "prereg-binding", "preregistration must be an object")
    _expect(prereg.get("status") == "Proposed", "prereg-binding", "preregistration status differs")
    _expect(prereg.get("lifecycle") == "planned", "prereg-binding", "preregistration lifecycle differs")
    _expect(prereg.get("evidence_status") == "open", "prereg-binding", "preregistration evidence status differs")
    _expect(prereg.get("technology_outcome") == "none", "prereg-binding", "preregistration technology outcome differs")
    _expect(prereg.get("execution_permitted") is False, "execution-disabled", "preregistration permits execution")
    materialization = prereg.get("development_materialization")
    _expect(type(materialization) is dict, "prereg-binding", "development materialization is missing")
    _expect(materialization.get("state") == "development-unfrozen" and materialization.get("not_evidence") is True and materialization.get("not_frozen") is True, "prereg-binding", "development materialization state differs")
    declarations: dict[str, dict[str, Any]] = {}
    corpora = materialization.get("corpora")
    _expect(type(corpora) is list and len(corpora) == 3, "prereg-binding", "preregistration corpus identities are incomplete")
    for index, item in enumerate(corpora):
        obj = _expect_keys(item, {"path", "bytes", "sha256"}, f"preregistration corpus {index}")
        path = obj["path"]
        _expect(path in {entry[1] for entry in PARTITIONS}, "prereg-binding", f"preregistration corpus {index} path is unexpected")
        _expect(path not in declarations, "prereg-binding", f"duplicate preregistration artifact {path}")
        declarations[path] = _identity_decl(item, f"preregistration corpus {index}", path)
    for key, path in (("recipe_manifest", "manifests/recipe-manifest.json"), ("sqrt_vectors", "sqrt-vectors.json")):
        declarations[path] = _identity_decl(materialization.get(key), f"preregistration {key}", path)
    declarations[GENERATOR_PATH] = _identity_decl(materialization.get("generator"), "preregistration generator", GENERATOR_PATH)
    artifact_decl = _identity_decl(materialization.get("artifact_manifest"), "preregistration artifact manifest", "manifests/artifact-manifest.json", allow_extra=True)
    _expect(materialization["artifact_manifest"].get("self_binding") is False and materialization["artifact_manifest"].get("listed_artifacts_exclude_manifest_itself") is True, "prereg-binding", "artifact manifest self-binding declaration differs")
    declarations[artifact_decl["path"]] = artifact_decl
    _expect(set(declarations) == PACKAGE_FILES | {GENERATOR_PATH}, "prereg-binding", "preregistration artifact identities differ from package")
    return declarations


def _read_and_validate_generator(root: Path, declaration: Mapping[str, Any]) -> bytes:
    raw = _regular_bytes(root / GENERATOR_PATH, GENERATOR_PATH, MAX_GENERATOR_BYTES)
    _expect(len(raw) == declaration["bytes"], "generator-size", "generator size differs from preregistration")
    _expect(hashlib.sha256(raw).hexdigest() == declaration["sha256"], "generator-hash", "generator hash differs from preregistration")
    return raw


def _read_and_validate_artifacts(root: Path, declarations: Mapping[str, Mapping[str, Any]]) -> tuple[dict[str, Any], dict[str, bytes]]:
    manifest_path = root / "manifests/artifact-manifest.json"
    manifest_identity = declarations["manifests/artifact-manifest.json"]
    manifest_raw = _regular_bytes(manifest_path, "artifact manifest", MAX_MANIFEST_BYTES, expected_size=manifest_identity["bytes"])
    _expect(hashlib.sha256(manifest_raw).hexdigest() == manifest_identity["sha256"], "prereg-binding", "artifact manifest differs from preregistration")
    manifest = _parse_json(manifest_raw, "artifact manifest", MAX_MANIFEST_BYTES)
    _expect_keys(manifest, {"artifacts", "execution_permitted", "generator", "schema", "status"}, "artifact manifest")
    _expect(manifest["schema"] == "ck.exp-0002.phase3.generated-artifacts-1", "manifest-identity", "artifact manifest schema differs")
    _expect(manifest["status"] == "development-unfrozen", "manifest-identity", "artifact manifest status differs")
    _expect(manifest["execution_permitted"] is False, "execution-disabled", "artifact manifest permits execution")
    _expect(manifest["generator"] == "scripts/generate_phase3.py", "manifest-identity", "artifact generator differs")
    entries = manifest["artifacts"]
    _expect(type(entries) is list and len(entries) == len(PACKAGE_FILES) - 1, "artifact-count", "artifact manifest has the wrong artifact count")
    by_path: dict[str, dict[str, Any]] = {}
    total = 0
    for index, item in enumerate(entries):
        obj = _expect_keys(item, {"bytes", "path", "sha256"}, f"artifact manifest entry {index}")
        path = _safe_relative(obj["path"], f"artifact manifest entry {index}.path")
        _expect(path != "manifests/artifact-manifest.json", "artifact-path", "artifact manifest cannot list itself")
        _expect(path not in by_path, "duplicate-artifact", f"duplicate artifact path {path}")
        size = obj["bytes"]
        _expect(type(size) is int and not isinstance(size, bool) and 0 <= size <= MAX_PACKAGE_BYTES, "artifact-size", f"artifact {path} has invalid byte count")
        digest = _hex_sha(obj["sha256"], f"artifact {path}.sha256")
        by_path[path] = {"bytes": size, "sha256": digest}
        total += size
    _expect(set(by_path) == PACKAGE_FILES - {"manifests/artifact-manifest.json"}, "artifact-path", "artifact manifest paths differ from package layout")
    _expect(total <= MAX_PACKAGE_BYTES, "resource-limit", "package artifact total exceeds bound")
    raw_by_path: dict[str, bytes] = {}
    for path, identity in by_path.items():
        declared = declarations.get(path)
        _expect(declared is not None and declared["bytes"] == identity["bytes"] and declared["sha256"] == identity["sha256"], "prereg-binding", f"artifact {path} differs from preregistration")
        limit = MAX_PARTITION_BYTES if path.startswith("corpora/") or path.endswith("recipe-manifest.json") else MAX_SQRT_BYTES
        raw = _regular_bytes(root / path, path, limit, expected_size=identity["bytes"])
        _expect(hashlib.sha256(raw).hexdigest() == identity["sha256"], "artifact-hash", f"artifact {path} hash differs from manifest")
        raw_by_path[path] = raw
    return manifest, raw_by_path


def _read_jsonl(raw: bytes, label: str, expected_count: int) -> list[dict[str, Any]]:
    _expect(len(raw) <= MAX_PARTITION_BYTES, "resource-limit", f"{label} exceeds partition bound")
    lines = raw.split(b"\n")
    if raw.endswith(b"\n"):
        lines.pop()
    _expect(len(lines) == expected_count, "partition-count", f"{label} has {len(lines)} records; expected {expected_count}")
    result: list[dict[str, Any]] = []
    for index, line in enumerate(lines):
        _expect(bool(line), "blank-line", f"{label} line {index + 1} is blank")
        _expect(not line.endswith(b"\r"), "line-ending", f"{label} line {index + 1} is not LF terminated")
        _expect(len(line) + 1 <= FRAME_BYTES, "line-too-large", f"{label} line {index + 1} exceeds {FRAME_BYTES} bytes")
        value = _parse_json(line, f"{label} line {index + 1}", FRAME_BYTES)
        _expect(type(value) is dict, "request-shape", f"{label} line {index + 1} is not an object")
        _expect(set(value) == REQUEST_KEYS, "request-shape", f"{label} line {index + 1} has unexpected request members")
        result.append(value)
    return result


def _validate_recipe_manifest(raw: bytes) -> dict[str, Any]:
    recipe = _parse_json(raw, "recipe manifest", MAX_MANIFEST_BYTES)
    _expect_keys(recipe, {
        "candidate_outcomes_used", "cases", "execution_permitted", "fixture", "order",
        "randomness", "replacement", "request_id_substitution", "schema", "status", "thresholds",
    }, "recipe manifest")
    _expect(recipe["schema"] == "ck.exp-0002.phase3.recipe-manifest-1", "manifest-identity", "recipe manifest schema differs")
    _expect(recipe["status"] == "development-unfrozen", "manifest-identity", "recipe manifest status differs")
    _expect(recipe["execution_permitted"] is False and recipe["candidate_outcomes_used"] is False, "execution-disabled", "recipe manifest execution binding is invalid")
    _expect(recipe["randomness"] == "none" and recipe["replacement"] == "prohibited", "manifest-identity", "recipe randomness/replacement differs")
    _expect(recipe["order"] == "development; then family/metric/class/stratum held-out; then controls as listed", "partition-order", "recipe order differs")
    fixture = _expect_keys(recipe["fixture"], {"path", "sha256"}, "recipe fixture")
    _expect(fixture == {"path": EXPECTED_FIXTURE_PATH, "sha256": EXPECTED_FIXTURE_SHA256}, "recipe-linkage", "recipe fixture declaration differs")
    substitution = _expect_keys(recipe["request_id_substitution"], {"formula", "global_ordinals", "only_per_attempt_request_byte_change"}, "request-id substitution")
    _expect(substitution == {
        "formula": EXPECTED_REQUEST_ID_FORMULA,
        "global_ordinals": "000..059",
        "only_per_attempt_request_byte_change": True,
    }, "request-linkage", "recipe request-id substitution differs")
    thresholds = _expect_keys(recipe["thresholds"], {"translation_bits", "full_chord_bits"}, "recipe thresholds")
    _expect(thresholds == {"translation_bits": EXPECTED_TRANSLATION_BITS, "full_chord_bits": EXPECTED_FULL_CHORD_BITS}, "recipe-linkage", "recipe thresholds differ")
    cases = recipe["cases"]
    _expect(type(cases) is list and len(cases) == EXPECTED_TOTAL_RECORDS, "recipe-count", "recipe manifest must contain 60 cases")
    case_ids: set[str] = set()
    for index, case in enumerate(cases):
        _expect_keys(case, CASE_KEYS, f"recipe case {index}")
        _expect(case["global_ordinal"] == index, "partition-order", f"recipe case {index} ordinal differs")
        _expect(isinstance(case["case_id"], str) and case["case_id"] not in case_ids, "duplicate-case-id", f"recipe case {index} has a duplicate case ID")
        case_ids.add(case["case_id"])
        _expect(case["metric"] in {"translation", "rotation"}, "recipe-case", f"recipe case {index} metric is invalid")
        _expect(type(case["dispatch_to_candidate"]) is bool, "dispatch-mismatch", f"recipe case {index} dispatch flag is invalid")
        _expect(isinstance(case["source_sha256"], str), "recipe-linkage", f"recipe case {index} source hash is invalid")
        _hex_sha(case["source_sha256"], f"recipe case {index} source hash")
        _expect(type(case["source_bytes"]) is int and case["source_bytes"] <= MAX_SOURCE_BYTES, "recipe-linkage", f"recipe case {index} source byte count is invalid")
        if index in range(52, 56):
            _validate_typed_expectation(case["typed_expectation"], f"recipe case {index}.typed_expectation", rejection=False)
        elif index == 59:
            _validate_typed_expectation(case["typed_expectation"], f"recipe case {index}.typed_expectation", rejection=True)
    expected_ids = list(EXPECTED_DEVELOPMENT_IDS)
    for family in EXPECTED_FAMILIES:
        for metric in ("translation", "rotation"):
            for cls in ("agree", "conflict"):
                for stratum_index, stratum in enumerate(EXPECTED_HELD_OUT_STRATA[cls], start=1):
                    expected_ids.append(f"phase3/{family}/{metric}/{cls}/{stratum}/{stratum_index}")
    expected_ids.extend(EXPECTED_CONTROL_IDS)
    _expect([case["case_id"] for case in cases] == expected_ids, "partition-order", "recipe case order/IDs differ from the preregistered ledger")
    for index, case in enumerate(cases):
        assignment = case["assignment"]
        if index < 8:
            _expect(assignment == "development" and case["expected_class"] == "development" and case["stratum"] == "explicit", "partition-role", f"development case {index} role differs")
            _expect(case["dispatch_to_candidate"] is True and case["domain_expectation"] in {"admitted", "typed-control"}, "dispatch-mismatch", f"development case {index} dispatch differs")
        elif index < 48:
            _expect(assignment == "held-out" and case["expected_class"] in {"agree", "conflict"} and case["domain_expectation"] == "admitted" and case["condition_expectation"] == "in-domain", "partition-role", f"held-out case {index} role differs")
            _expect(case["dispatch_to_candidate"] is True, "dispatch-mismatch", f"held-out case {index} must dispatch")
        elif index < 52:
            _expect(assignment == "gray-band" and case["expected_class"] == "control" and case["stratum"] == "gray-band" and case["dispatch_to_candidate"] is True, "partition-role", f"gray control {index} role differs")
        elif index < 56:
            _expect(assignment == "candidate-local-admission" and case["expected_class"] == "control" and case["condition_expectation"] == "typed-control" and case["dispatch_to_candidate"] is True, "partition-role", f"typed control {index} role differs")
        elif index < 59:
            _expect(assignment == "out-of-domain-numeric" and case["condition_expectation"] == "runner-preflight" and case["dispatch_to_candidate"] is False, "dispatch-mismatch", f"preflight control {index} dispatch differs")
        else:
            _expect(assignment == "out-of-domain-numeric" and case["dispatch_to_candidate"] is True and case["typed_expectation"]["status"] == "rejected", "dispatch-mismatch", "negative-relative control dispatch differs")
    return recipe


def _validate_request(row: Mapping[str, Any], recipe_case: Mapping[str, Any], ordinal: int, label: str) -> None:
    _expect(row["protocol_id"] == EXPECTED_PROTOCOL, "request-linkage", f"{label} protocol differs")
    _expect(row["operation"] == EXPECTED_OPERATION and row["resource_profile"] == EXPECTED_RESOURCE_PROFILE, "request-linkage", f"{label} operation/profile differs")
    _expect(row["providers"] == EXPECTED_PROVIDERS, "request-linkage", f"{label} providers differ")
    request_id = row["request_id"]
    _expect(isinstance(request_id, str) and len(request_id.encode("utf-8")) <= MAX_REQUEST_ID_BYTES, "request-id", f"{label} request ID is invalid")
    _expect(request_id == f"p3-{{attempt_id}}-{ordinal:03d}", "request-linkage", f"{label} request ID differs from recipe ordinal")
    source = row["source"]
    _expect(isinstance(source, str), "request-shape", f"{label} source is not a string")
    try:
        source_raw = source.encode("utf-8")
    except UnicodeEncodeError as error:
        raise MaterializedAdapterError("invalid-utf8", f"{label} source is not valid UTF-8") from error
    _expect(len(source_raw) <= MAX_SOURCE_BYTES, "source-size", f"{label} source exceeds {MAX_SOURCE_BYTES} bytes")
    _parse_json(source_raw, f"{label} source", MAX_SOURCE_BYTES)
    _expect(len(source_raw) == recipe_case["source_bytes"], "recipe-linkage", f"{label} source byte count differs from recipe")
    _expect(hashlib.sha256(source_raw).hexdigest() == recipe_case["source_sha256"], "recipe-linkage", f"{label} source hash differs from recipe")
    tolerances = row["tolerances"]
    _expect(type(tolerances) is dict and set(tolerances) == TOLERANCE_KEYS, "request-shape", f"{label} tolerances are not closed")
    expected_relative = -1.0 if ordinal == 59 else 0.0
    expected = {
        "translation_absolute": bits_to_float(EXPECTED_TRANSLATION_BITS),
        "translation_relative": expected_relative,
        "rotation_half_chord": bits_to_float(EXPECTED_HALF_CHORD_BITS),
    }
    def tolerance_bits(value: Any, key: str) -> str:
        _expect(not isinstance(value, bool) and isinstance(value, (int, float, Decimal)), "request-shape", f"{label} tolerance {key} must be a JSON number")
        try:
            numeric = float(value)
        except (TypeError, ValueError, OverflowError) as error:
            raise MaterializedAdapterError("request-linkage", f"{label} tolerance {key} is not finite binary64") from error
        _expect(math.isfinite(numeric), "request-linkage", f"{label} tolerance {key} is not finite")
        return float_to_bits(numeric)
    _expect(all(tolerance_bits(tolerances[key], key) == float_to_bits(expected[key]) for key in TOLERANCE_KEYS), "request-linkage", f"{label} tolerances differ")


def _project_case(row: Mapping[str, Any], recipe_case: Mapping[str, Any], ordinal: int) -> dict[str, Any]:
    # The output is intentionally assembled field-by-field rather than copying
    # recipe metadata.  This is the held-out opacity boundary.
    projected: dict[str, Any] = {
        "protocol_id": EXPECTED_PROTOCOL,
        "request_id": row["request_id"],
        "operation": EXPECTED_OPERATION,
        "resource_profile": EXPECTED_RESOURCE_PROFILE,
        "source": row["source"],
        # Keep exact Decimal tokens; the existing runner validates bounded
        # Decimal values without a binary-float round trip.
        "tolerances": dict(row["tolerances"]),
        "providers": dict(row["providers"]),
        "metric": recipe_case["metric"],
    }
    if not recipe_case["dispatch_to_candidate"]:
        projected["dispatch_to_candidate"] = False
    if ordinal < 8 or ordinal >= 48:
        projected["observation_only"] = True
    if ordinal == 59:
        expectation = recipe_case["typed_expectation"]
        projected["expected_response_status"] = expectation["status"]
        projected["expected_cause"] = dict(expectation["cause"])
    return projected


def _load_materialized(package_root: str | os.PathLike[str]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Validate a package and retain held-out labels only for internal handoff."""
    root = _absolute_path(package_root)
    _reject_symlink_components(root, "package root")
    _check_layout(root)
    prereg_raw = _regular_bytes(root / PREREGISTRATION_PATH, PREREGISTRATION_PATH, MAX_PREREG_BYTES)
    declarations = _validate_preregistration(prereg_raw)
    _read_and_validate_generator(root, declarations[GENERATOR_PATH])
    _, artifact_raw = _read_and_validate_artifacts(root, declarations)
    sqrt_value = _parse_json(artifact_raw["sqrt-vectors.json"], "sqrt vectors", MAX_SQRT_BYTES)
    try:
        verification = oracle.verify_sqrt_vectors(sqrt_value)
    except (oracle.OracleError, Phase3Error, TypeError, ValueError) as error:
        raise MaterializedAdapterError("sqrt-vectors", f"sqrt vector verification failed: {getattr(error, 'code', 'invalid')}") from error
    _expect(verification.get("checked") == 12 and verification.get("certified") is True, "sqrt-vectors", "sqrt vector fixture is incomplete")
    recipe = _validate_recipe_manifest(artifact_raw["manifests/recipe-manifest.json"])
    partitions: list[dict[str, Any]] = []
    heldout_classes: dict[str, str] = {}
    raw_partitions: list[tuple[str, list[dict[str, Any]]]] = []
    all_row_ids: list[Any] = []
    for role, path, expected_count in PARTITIONS:
        rows = _read_jsonl(artifact_raw[path], f"{role} partition", expected_count)
        raw_partitions.append((role, rows))
        all_row_ids.extend(row.get("request_id") for row in rows)
    _expect(all(isinstance(request_id, str) for request_id in all_row_ids), "request-id", "materialized request IDs must be strings")
    _expect(len(all_row_ids) == len(set(all_row_ids)), "duplicate-request-id", "materialized partitions contain duplicate request IDs")
    ordinal = 0
    for role, rows in raw_partitions:
        for line_index, row in enumerate(rows):
            recipe_case = recipe["cases"][ordinal]
            _validate_request(row, recipe_case, ordinal, f"{role} line {line_index + 1}")
            partitions.append(_project_case(row, recipe_case, ordinal))
            if 8 <= ordinal < 48:
                heldout_classes[row["request_id"]] = recipe_case["expected_class"]
            ordinal += 1
    _expect(ordinal == EXPECTED_TOTAL_RECORDS, "partition-count", "materialized partition total differs")
    ids = [case["request_id"] for case in partitions]
    _expect(len(ids) == len(set(ids)), "duplicate-request-id", "materialized request IDs are not unique")
    return partitions, heldout_classes


def load_materialized_cases(package_root: str | os.PathLike[str]) -> list[dict[str, Any]]:
    """Validate ``package_root`` and return closed synthetic runner cases.

    No filesystem path, construction target, semantic expected class, or source
    truth is present in the returned objects.  Materialized request IDs remain
    the exact ``p3-{attempt_id}-NNN`` placeholders; the non-evidence wrapper is
    the only place that maps them to the runner's synthetic-ID namespace.
    """
    return _load_materialized(package_root)[0]


def _rewrite_response_id(raw: bytes, materialized_id: str, synthetic_id: str) -> bytes:
    """Rewrite one validated echoed ID while retaining malformed frames for the runner."""
    try:
        value = _parse_json(raw, "mapped response", FRAME_BYTES, response_numbers=True)
    except MaterializedAdapterError:
        return raw
    if type(value) is not dict:
        return raw
    echoed_id = value.get("request_id")
    if echoed_id == materialized_id:
        value["request_id"] = synthetic_id
    elif isinstance(echoed_id, str):
        # A parsed response for a materialized key must prove that it echoed
        # that exact key before the private rewrite.  Pin a wrong-but-well-
        # formed echo to the materialized placeholder so the runner observes
        # a request-ID mismatch even when the response guessed the synthetic
        # internal ID.
        value["request_id"] = materialized_id
    else:
        return raw
    try:
        return canonical_json(value)
    except Phase3Error as error:
        raise MaterializedAdapterError("response-rewrite", f"mapped response cannot be re-encoded: {error.code}") from error


def _transcript_items(transcript: Any) -> list[tuple[str, bytes]]:
    _expect(isinstance(transcript, Mapping), "transcript-shape", "transcript must be a mapping")
    try:
        items = list(transcript.items())
    except (AttributeError, TypeError, ValueError, RuntimeError) as error:
        raise MaterializedAdapterError("transcript-shape", "transcript mapping cannot be enumerated") from error
    checked: list[tuple[str, bytes]] = []
    for request_id, raw in items:
        _expect(isinstance(request_id, str) and bool(request_id), "transcript-key", "transcript keys must be non-empty strings")
        try:
            encoded_id = request_id.encode("utf-8")
        except UnicodeEncodeError as error:
            raise MaterializedAdapterError("transcript-key", "transcript key is not valid UTF-8") from error
        _expect(len(encoded_id) <= MAX_REQUEST_ID_BYTES, "transcript-key", "transcript key exceeds the request-ID bound")
        _expect(type(raw) is bytes, "transcript-shape", "transcript must map string IDs to bytes")
        checked.append((request_id, raw))
    return checked


def _extra_request_id(index: int, original: str, used: set[str]) -> str:
    digest = hashlib.sha256(original.encode("utf-8")).hexdigest()
    for salt in range(1024):
        suffix = f"-{salt}" if salt else ""
        candidate = f"{EXTRA_REQUEST_ID_PREFIX}{index:03d}-{digest}{suffix}"
        _expect(len(candidate.encode("utf-8")) <= MAX_REQUEST_ID_BYTES, "transcript-key", "internal extra request ID exceeds the request-ID bound")
        if candidate not in used:
            return candidate
    _fail("transcript-id-collision", "cannot allocate a collision-free internal extra request ID")


def run_materialized(package_root: str | os.PathLike[str], transcript: Mapping[str, bytes]) -> dict[str, Any]:
    """Load a package and hand its projected cases to ``run_synthetic`` only."""
    materialized, heldout_classes = _load_materialized(package_root)
    transcript_items = _transcript_items(transcript)
    # The package's p3-{attempt_id}-NNN IDs are retained by the loader.  The
    # synthetic runner has a deliberately narrower test-only ID namespace, so
    # this reversible mapping exists only inside this non-evidence wrapper.
    synthetic: list[dict[str, Any]] = []
    id_map: dict[str, str] = {}
    for ordinal, case in enumerate(materialized):
        mapped = dict(case)
        materialized_id = case["request_id"]
        synthetic_id = f"synthetic/phase3/{ordinal:03d}"
        id_map[materialized_id] = synthetic_id
        mapped["request_id"] = synthetic_id
        if 8 <= ordinal < 48:
            mapped["expected_class"] = heldout_classes[materialized_id]
        synthetic.append(mapped)
    mapped_transcript: dict[str, bytes] = {}
    extra_ids: dict[str, str] = {}
    used_ids = set(id_map.values())
    for index, (request_id, raw) in enumerate(transcript_items):
        if request_id in id_map:
            synthetic_id = id_map[request_id]
            raw = _rewrite_response_id(raw, request_id, synthetic_id)
        else:
            synthetic_id = _extra_request_id(index, request_id, used_ids | set(mapped_transcript))
            extra_ids[synthetic_id] = request_id
        _expect(synthetic_id not in mapped_transcript, "transcript-id-collision", f"transcript keys collide after internal mapping at {synthetic_id}")
        mapped_transcript[synthetic_id] = raw
    result = runner.run_synthetic(synthetic, mapped_transcript)
    for entry in result.get("entries", []):
        internal_id = entry.get("request_id")
        if internal_id in extra_ids:
            entry["request_id"] = extra_ids[internal_id]
    return result


__all__ = ["MaterializedAdapterError", "load_materialized_cases", "run_materialized"]

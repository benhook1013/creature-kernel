#!/usr/bin/env python3
"""Parser-independent consistency preflight for the Readiness 2 fixture envelope.

This tool deliberately does not parse fixture body documents or claim that the
expected results are correct.  It only checks the manifest's internal
references, hashes, resource byte bound, and the external raw path-set binding.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import stat
import struct
import sys
from typing import Any, Iterable


FRAME = "ck.path-set.raw.v1"
FRAME_BYTES = FRAME.encode("ascii") + b"\0"
SAFE_ID = re.compile(r"[a-z][a-z0-9_-]*\Z")
PROFILE_ID = re.compile(r"[a-z][a-z0-9_.-]*\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
SAFE_PATH = re.compile(r"[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*\Z")
MODES = {0o100644, 0o100755}
R2_DIAGNOSTIC_PROFILE = "ck.diagnostic.r2"
R2_RESOURCE_LIMITS = {
    "ck.resource.body.r2": {
        "max_source_bytes": 65_536,
        "max_nesting_depth": 64,
        "max_json_values": 8_192,
        "max_object_members": 4_096,
        "max_array_items": 4_096,
        "max_string_bytes": 16_384,
        "max_number_token_bytes": 256,
        "max_diagnostics": 64,
    },
    "ck.resource.body.r2-tight": {
        "max_source_bytes": 128,
        "max_nesting_depth": 64,
        "max_json_values": 8_192,
        "max_object_members": 4_096,
        "max_array_items": 4_096,
        "max_string_bytes": 16_384,
        "max_number_token_bytes": 256,
        "max_diagnostics": 64,
    },
}
R2_SUITE_ID = "body-document-readiness-2"
R2_SCHEMA_PATH = "spec/body-document/schema/ck-body-document-v1.schema.json"
R2_FIXTURE_IDS = {
    "minimal-valid-envelope",
    "optional-module-absent",
    "duplicate-member",
    "invalid-discriminator",
    "unsupported-revision",
    "unknown-core-member",
    "unsupported-required-extension",
    "optional-extension-opaque",
    "resource-over-budget",
}
R2_DIAGNOSTIC_CODES = {
    "ck.resource.source-bytes",
    "ck.resource.json-work",
    "ck.source.invalid-json",
    "ck.source.duplicate-member",
    "ck.contract.invalid-discriminator",
    "ck.contract.unsupported-family",
    "ck.contract.unsupported-revision",
    "ck.source.schema",
    "ck.extension.unsupported-required",
    "ck.internal.schema",
}


class PreflightError(Exception):
    """A concise, deterministic user-facing preflight failure."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def _pairs_reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PreflightError("duplicate JSON member")
        result[key] = value
    return result


def _reject_constant(value: str) -> Any:
    raise PreflightError("non-finite JSON number")


def _parse_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise PreflightError("non-finite JSON number")
    return number


def _parse_json(data: bytes) -> Any:
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise PreflightError("manifest is not strict UTF-8") from exc
    try:
        return json.loads(
            text,
            object_pairs_hook=_pairs_reject_duplicates,
            parse_constant=_reject_constant,
            parse_float=_parse_float,
        )
    except PreflightError:
        raise
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise PreflightError("manifest is not valid JSON") from exc


def _object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PreflightError(f"{name} must be an object")
    return value


def _closed(value: Any, expected: set[str], name: str) -> dict[str, Any]:
    obj = _object(value, name)
    if set(obj) != expected:
        raise PreflightError(f"{name} has unknown or missing member")
    return obj


def _string(value: Any, name: str, *, nonempty: bool = False) -> str:
    if not isinstance(value, str) or (nonempty and not value):
        raise PreflightError(f"{name} must be a string")
    return value


def _integer(value: Any, name: str) -> int:
    if type(value) is not int:  # bool is intentionally not an integer here.
        raise PreflightError(f"{name} must be an integer")
    return value


def _boolean(value: Any, name: str) -> bool:
    if type(value) is not bool:
        raise PreflightError(f"{name} must be boolean")
    return value


def _const(value: Any, expected: Any, name: str) -> None:
    if value != expected or type(value) is not type(expected):
        raise PreflightError(f"{name} has invalid value")


def _safe_id(value: Any, name: str) -> str:
    value = _string(value, name, nonempty=True)
    if SAFE_ID.fullmatch(value) is None:
        raise PreflightError(f"{name} is not a safe identifier")
    return value


def _profile_id(value: Any, name: str) -> str:
    value = _string(value, name, nonempty=True)
    if PROFILE_ID.fullmatch(value) is None:
        raise PreflightError(f"{name} is not a safe profile identifier")
    return value


def _sha(value: Any, name: str) -> str:
    value = _string(value, name)
    if SHA256.fullmatch(value) is None:
        raise PreflightError(f"{name} is not a lowercase SHA-256")
    return value


def _safe_path(value: Any, name: str) -> str:
    value = _string(value, name, nonempty=True)
    if "\\" in value or "\x00" in value or value.startswith("/"):
        raise PreflightError(f"{name} is not a safe relative path")
    components = value.split("/")
    if any(component in ("", ".", "..") for component in components):
        raise PreflightError(f"{name} is not a normalized relative path")
    if SAFE_PATH.fullmatch(value) is None:
        raise PreflightError(f"{name} is not a safe ASCII relative path")
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise PreflightError(f"{name} is not valid UTF-8") from exc
    return value


def _open_root(root: str) -> int:
    try:
        fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        info = os.fstat(fd)
    except OSError as exc:
        raise PreflightError("repository root is not an accessible directory") from exc
    if not stat.S_ISDIR(info.st_mode):
        os.close(fd)
        raise PreflightError("repository root is not a directory")
    return fd


def _path_components(path: str) -> list[str]:
    # _safe_path has already checked this; keeping traversal in one helper
    # makes it difficult for a later caller to accidentally use host joins.
    return path.split("/")


def _read_relative(root_fd: int, path: str) -> tuple[bytes, int]:
    """Read one regular file through descriptor-relative no-follow traversal."""
    ancestors: list[int] = []
    current = root_fd
    components = _path_components(path)
    try:
        for component in components[:-1]:
            try:
                next_fd = os.open(
                    component,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                    dir_fd=current,
                )
            except OSError as exc:
                raise PreflightError("path ancestor is invalid") from exc
            info = os.fstat(next_fd)
            if not stat.S_ISDIR(info.st_mode):
                os.close(next_fd)
                raise PreflightError("path ancestor is invalid")
            ancestors.append(next_fd)
            current = next_fd

        try:
            fd = os.open(
                components[-1],
                os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=current,
            )
        except OSError as exc:
            raise PreflightError("path file is unavailable") from exc
        try:
            before = os.fstat(fd)
            mode = stat.S_IFMT(before.st_mode) | stat.S_IMODE(before.st_mode)
            if not stat.S_ISREG(before.st_mode):
                raise PreflightError("path is not a regular file")
            if before.st_nlink != 1:
                raise PreflightError("path regular file has multiple links")
            if mode not in MODES:
                raise PreflightError("path mode is not 100644 or 100755")
            chunks: list[bytes] = []
            remaining = before.st_size
            while remaining:
                chunk = os.read(fd, min(1024 * 1024, remaining))
                if not chunk:
                    raise PreflightError("path size changed while reading")
                chunks.append(chunk)
                remaining -= len(chunk)
            after = os.fstat(fd)
            before_identity = (before.st_dev, before.st_ino, before.st_mode, before.st_size)
            after_identity = (after.st_dev, after.st_ino, after.st_mode, after.st_size)
            if before_identity != after_identity:
                raise PreflightError("path identity changed while reading")
            return b"".join(chunks), stat.S_IFMT(before.st_mode) | stat.S_IMODE(before.st_mode)
        finally:
            os.close(fd)
    finally:
        for ancestor_fd in reversed(ancestors):
            os.close(ancestor_fd)


def _validate_manifest(
    value: Any, *, enforce_exact_r2: bool
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest = _closed(value, {"contract", "suite", "schema", "profiles", "fixtures"}, "manifest")
    contract = _closed(manifest["contract"], {"family", "revision"}, "contract")
    _const(contract["family"], "creature-kernel.fixture-manifest", "contract.family")
    if _integer(contract["revision"], "contract.revision") != 1:
        raise PreflightError("contract.revision has invalid value")

    suite = _closed(manifest["suite"], {"id", "kind"}, "suite")
    suite_id = _safe_id(suite["id"], "suite.id")
    if enforce_exact_r2:
        _const(suite_id, R2_SUITE_ID, "suite.id")
    _const(suite["kind"], "body-document-admission", "suite.kind")

    schema = _closed(manifest["schema"], {"path", "sha256", "draft", "contract_family", "revision"}, "schema")
    schema_path = _safe_path(schema["path"], "schema.path")
    if enforce_exact_r2:
        _const(schema_path, R2_SCHEMA_PATH, "schema.path")
    _sha(schema["sha256"], "schema.sha256")
    _const(schema["draft"], "2020-12", "schema.draft")
    _const(schema["contract_family"], "creature-kernel.body", "schema.contract_family")
    if _integer(schema["revision"], "schema.revision") != 1:
        raise PreflightError("schema.revision has invalid value")

    profiles = _closed(manifest["profiles"], {"diagnostic", "resources"}, "profiles")
    diagnostic = _closed(profiles["diagnostic"], {"id"}, "profiles.diagnostic")
    diagnostic_id = _profile_id(diagnostic["id"], "profiles.diagnostic.id")
    if diagnostic_id != R2_DIAGNOSTIC_PROFILE:
        raise PreflightError("diagnostic profile does not match R2 contract")
    resources = profiles["resources"]
    if not isinstance(resources, list) or not resources:
        raise PreflightError("profiles.resources must be nonempty")
    resource_limits: dict[str, dict[str, int]] = {}
    for index, resource_value in enumerate(resources):
        resource = _closed(
            resource_value,
            {
                "id",
                "max_source_bytes",
                "max_nesting_depth",
                "max_json_values",
                "max_object_members",
                "max_array_items",
                "max_string_bytes",
                "max_number_token_bytes",
                "max_diagnostics",
            },
            f"profiles.resources[{index}]",
        )
        resource_id = _profile_id(resource["id"], f"profiles.resources[{index}].id")
        if resource_id in resource_limits:
            raise PreflightError("duplicate resource profile ID")
        values = {
            key: _integer(resource[key], f"profiles.resources[{index}].{key}")
            for key in resource
            if key != "id"
        }
        if any(value < 1 for value in values.values()):
            raise PreflightError("resource profile limit is out of range")
        resource_limits[resource_id] = values
    if resource_limits != R2_RESOURCE_LIMITS:
        raise PreflightError("resource profiles do not match R2 contract")

    fixtures_value = manifest["fixtures"]
    if not isinstance(fixtures_value, list) or not fixtures_value:
        raise PreflightError("fixtures must be nonempty")
    fixtures: list[dict[str, Any]] = []
    fixture_ids: set[str] = set()
    fixture_paths: set[str] = set()
    for index, fixture_value in enumerate(fixtures_value):
        name = f"fixtures[{index}]"
        fixture = _closed(
            fixture_value,
            {"id", "path", "sha256", "purpose", "provenance", "operation", "profiles", "expected"},
            name,
        )
        fixture_id = _safe_id(fixture["id"], f"{name}.id")
        if fixture_id in fixture_ids:
            raise PreflightError("duplicate fixture ID")
        fixture_ids.add(fixture_id)
        path = _safe_path(fixture["path"], f"{name}.path")
        if path in fixture_paths:
            raise PreflightError("duplicate fixture path")
        fixture_paths.add(path)
        _sha(fixture["sha256"], f"{name}.sha256")
        _string(fixture["purpose"], f"{name}.purpose", nonempty=True)
        provenance = _closed(fixture["provenance"], {"kind", "source", "license"}, f"{name}.provenance")
        _const(provenance["kind"], "authored", f"{name}.provenance.kind")
        _string(provenance["source"], f"{name}.provenance.source", nonempty=True)
        _const(provenance["license"], "project", f"{name}.provenance.license")
        _const(fixture["operation"], "validate", f"{name}.operation")
        fixture_profiles = _closed(fixture["profiles"], {"diagnostic", "resource"}, f"{name}.profiles")
        if _profile_id(fixture_profiles["diagnostic"], f"{name}.profiles.diagnostic") != diagnostic_id:
            raise PreflightError("fixture diagnostic profile does not resolve")
        resource_id = _profile_id(fixture_profiles["resource"], f"{name}.profiles.resource")
        if resource_id not in resource_limits:
            raise PreflightError("fixture resource profile does not resolve")
        expected = _object(fixture["expected"], f"{name}.expected")
        if set(expected) - {"status", "processing_complete", "diagnostics_complete", "primary_diagnostic"}:
            raise PreflightError(f"{name}.expected has unknown member")
        required_expected = {"status", "processing_complete", "diagnostics_complete"}
        if set(expected) & required_expected != required_expected:
            raise PreflightError(f"{name}.expected has missing member")
        status = _string(expected["status"], f"{name}.expected.status")
        if status not in {"success", "invalid-source", "unsupported", "resource-limit"}:
            raise PreflightError(f"{name}.expected.status has invalid value")
        _boolean(expected["processing_complete"], f"{name}.expected.processing_complete")
        _boolean(expected["diagnostics_complete"], f"{name}.expected.diagnostics_complete")
        if expected["processing_complete"] != (status != "resource-limit"):
            raise PreflightError(f"{name}.expected.processing_complete has invalid value")
        if not expected["diagnostics_complete"]:
            raise PreflightError(f"{name}.expected.diagnostics_complete has invalid value")
        has_primary = "primary_diagnostic" in expected
        if status == "success" and has_primary:
            raise PreflightError("success fixture must not have primary diagnostic")
        if status != "success":
            if not has_primary:
                raise PreflightError("non-success fixture requires primary diagnostic")
            primary = _profile_id(
                expected["primary_diagnostic"],
                f"{name}.expected.primary_diagnostic",
            )
            if primary not in R2_DIAGNOSTIC_CODES:
                raise PreflightError("fixture primary diagnostic is not in the R2 registry")
        fixture_copy = dict(fixture)
        fixture_copy["_resource_id"] = resource_id
        fixture_copy["_resource_limit"] = resource_limits[resource_id]
        fixtures.append(fixture_copy)

    if enforce_exact_r2 and fixture_ids != R2_FIXTURE_IDS:
        raise PreflightError("fixture IDs do not match the exact R2 corpus")

    # The manifest path and schema path are added by the caller, but duplicate
    # fixture paths are checked here before any filesystem reads occur.
    return schema, fixtures


def _binding(entries: Iterable[tuple[str, int, bytes]]) -> str:
    ordered = sorted(entries, key=lambda item: item[0].encode("utf-8"))
    digest = hashlib.sha256()
    digest.update(FRAME_BYTES)
    seen: set[str] = set()
    for path, mode, content in ordered:
        if path in seen:
            raise PreflightError("duplicate path in binding")
        seen.add(path)
        path_bytes = path.encode("utf-8")
        digest.update(struct.pack(">I", len(path_bytes)))
        digest.update(path_bytes)
        digest.update(struct.pack(">I", mode))
        digest.update(struct.pack(">Q", len(content)))
        digest.update(content)
    return digest.hexdigest()


def _run(root: str, manifest_path: str, *, enforce_exact_r2: bool) -> dict[str, Any]:
    _safe_path(manifest_path, "manifest path")
    root_fd = _open_root(root)
    try:
        manifest_bytes, manifest_mode = _read_relative(root_fd, manifest_path)
        manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
        parsed = _parse_json(manifest_bytes)
        schema, fixtures = _validate_manifest(parsed, enforce_exact_r2=enforce_exact_r2)

        paths = {manifest_path}
        schema_path = schema["path"]
        if schema_path in paths:
            raise PreflightError("duplicate path in binding")
        paths.add(schema_path)
        schema_bytes, schema_mode = _read_relative(root_fd, schema_path)
        if hashlib.sha256(schema_bytes).hexdigest() != schema["sha256"]:
            raise PreflightError("schema hash mismatch")
        entries: list[tuple[str, int, bytes]] = [(manifest_path, manifest_mode, manifest_bytes), (schema_path, schema_mode, schema_bytes)]

        for fixture in fixtures:
            path = fixture["path"]
            if path in paths:
                raise PreflightError("duplicate path in binding")
            paths.add(path)
            content, mode = _read_relative(root_fd, path)
            if hashlib.sha256(content).hexdigest() != fixture["sha256"]:
                raise PreflightError("fixture hash mismatch")
            over = len(content) > fixture["_resource_limit"]["max_source_bytes"]
            is_resource_limit = fixture["expected"]["status"] == "resource-limit"
            if is_resource_limit != over:
                raise PreflightError("fixture resource-limit status does not match source-byte limit")
            entries.append((path, mode, content))
        return {
            "manifest_sha256": manifest_sha,
            "path_set": {"framing": FRAME, "sha256": _binding(entries)},
        }
    finally:
        os.close(root_fd)


def run(root: str, manifest_path: str) -> dict[str, Any]:
    """Preflight the one exact Readiness 2 body-document corpus."""
    return _run(root, manifest_path, enforce_exact_r2=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="check Readiness 2 fixture manifest consistency")
    parser.add_argument("repository_root")
    parser.add_argument("manifest_path")
    args = parser.parse_args(argv)
    try:
        result = run(args.repository_root, args.manifest_path)
    except PreflightError as exc:
        print(f"preflight: {exc.message}", file=sys.stderr)
        return 1
    except OSError:
        print("preflight: filesystem read failed", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

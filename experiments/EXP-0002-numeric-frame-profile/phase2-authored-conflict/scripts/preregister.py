#!/usr/bin/env python3
"""Safe preregistration preflight for the EXP-0002 authored-conflict successor.

This draft-only package validates and identifies a plan. It cannot transition
to an executable registration, load a corpus, run a candidate, or create an
experiment result or receipt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import stat
import sys
from pathlib import Path
from typing import Any, Mapping


SCHEMA = "ck.exp-0002.r3-authored-conflict-preregistration-1"
EXPERIMENT_ID = "EXP-0002"
DEFAULT_MANIFEST = Path(__file__).resolve().parents[1] / "preregistration.json"
ROLES = ("development", "held-out", "adversarial")
PROTOCOL_DRAFT_ID = "ck.r3.authored-conflict-successor-draft-1"
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
MAX_MANIFEST_BYTES = 1024 * 1024
MAX_JSON_DEPTH = 32
MAX_CONTENT_REFERENCES = 3
MAX_REFERENCE_BYTES = 64 * 1024 * 1024
MAX_AGGREGATE_REFERENCE_BYTES = 128 * 1024 * 1024

CANONICAL_REFERENCE_TRIPLES = (
    (
        "dr-0008-revision-14",
        "docs/decisions/DR-0008-first-digitigrade-morphology-and-embodiment-envelope.md",
        "r3-boundary-contract",
    ),
    (
        "numeric-frame-research-design",
        "docs/research/numeric-frame-profile-experiment.md",
        "successor-evidence-design",
    ),
    (
        "exp-0002-phase-one-boundary",
        "experiments/EXP-0002-numeric-frame-profile/README.md",
        "phase-one-lineage-boundary",
    ),
)

BASE_GRAPH_CONSTRAINTS = (
    "finite",
    "schema-valid",
    "duplicate-free",
    "acyclic",
    "resource-admitted",
    "valid-endpoints-and-capacity",
)
FIXTURE_DEFINITIONS = (
    (
        "supported-valid",
        "supported-digitigrade",
        "valid-supported",
        None,
        BASE_GRAPH_CONSTRAINTS,
    ),
    (
        "supported-extra-limb-invalid",
        "supported-digitigrade",
        "semantically-invalid",
        "invalid-source",
        BASE_GRAPH_CONSTRAINTS + ("supported-profile-invariant-contradiction-extra-limb",),
    ),
    (
        "quadruped-unsupported",
        "explicit-quadruped",
        "well-formed-but-unsupported",
        "unsupported",
        BASE_GRAPH_CONSTRAINTS + ("unsupported-profile-is-sole-non-success-reason",),
    ),
    (
        "extra-limb-unsupported",
        "explicit-extra-limb",
        "well-formed-but-unsupported",
        "unsupported",
        BASE_GRAPH_CONSTRAINTS + ("unsupported-profile-is-sole-non-success-reason",),
    ),
    (
        "freeform-attachment-unsupported",
        "explicit-freeform-attachment-topology",
        "well-formed-but-unsupported",
        "unsupported",
        BASE_GRAPH_CONSTRAINTS + ("unsupported-profile-is-sole-non-success-reason",),
    ),
)


class PreflightError(ValueError):
    """A deterministic, user-actionable manifest or content error."""


def _exact_fields(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        details: list[str] = []
        if missing:
            details.append("missing=" + ",".join(missing))
        if extra:
            details.append("unknown=" + ",".join(extra))
        raise PreflightError(f"{label} fields invalid ({'; '.join(details)})")


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PreflightError(f"{label} must be an object")
    return value


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise PreflightError(f"{label} must be an array")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise PreflightError(f"{label} must be a non-empty string")
    return value


def _id(value: Any, label: str) -> str:
    value = _string(value, label)
    if not ID_RE.fullmatch(value):
        raise PreflightError(f"{label} is not a stable lowercase identifier")
    return value


def _bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise PreflightError(f"{label} must be boolean")
    return value


def _nullable_string(value: Any, label: str) -> None:
    if value is not None and (not isinstance(value, str) or not value):
        raise PreflightError(f"{label} must be null or a non-empty string")


def _nullable_sha(value: Any, label: str) -> None:
    if value is not None and (not isinstance(value, str) or not SHA256_RE.fullmatch(value)):
        raise PreflightError(f"{label} must be null or a lowercase SHA-256 digest")


def _read_manifest(path: Path) -> bytes:
    try:
        if path.is_symlink() or not path.is_file():
            raise PreflightError("manifest must be a regular non-symlink file")
        with path.open("rb") as handle:
            raw = handle.read(MAX_MANIFEST_BYTES + 1)
    except PreflightError:
        raise
    except OSError as exc:
        raise PreflightError(f"cannot read manifest: {exc}") from exc
    if len(raw) > MAX_MANIFEST_BYTES:
        raise PreflightError(f"manifest exceeds {MAX_MANIFEST_BYTES} bytes")
    if not raw:
        raise PreflightError("manifest is empty")
    return raw


def _validate_json_tree(value: Any) -> None:
    stack: list[tuple[Any, int, str]] = [(value, 0, "manifest")]
    while stack:
        node, depth, label = stack.pop()
        if depth > MAX_JSON_DEPTH:
            raise PreflightError(f"manifest JSON nesting exceeds {MAX_JSON_DEPTH} at {label}")
        if isinstance(node, float) and not math.isfinite(node):
            raise PreflightError(f"non-finite number at {label}")
        if isinstance(node, dict):
            stack.extend((child, depth + 1, f"{label}.{key}") for key, child in node.items())
        elif isinstance(node, list):
            stack.extend((child, depth + 1, f"{label}[{index}]") for index, child in enumerate(node))


def _parse_json(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = _read_manifest(path)

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise PreflightError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                PreflightError(f"non-finite JSON constant is not permitted: {token}")
            ),
        )
    except PreflightError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, TypeError, ValueError) as exc:
        raise PreflightError(f"manifest is not bounded strict UTF-8 JSON: {exc}") from exc
    manifest = _object(value, "manifest")
    try:
        _validate_json_tree(manifest)
    except RecursionError as exc:
        raise PreflightError("manifest JSON nesting exceeds the supported bound") from exc
    return manifest, raw


def _validate_identity_binding(value: Any, label: str, expected_state: str) -> dict[str, Any]:
    binding = _object(value, label)
    _exact_fields(binding, {"state", "id", "content_sha256", "required_before_execution"}, label)
    if binding["state"] != expected_state:
        raise PreflightError(f"{label}.state must be {expected_state}")
    _nullable_string(binding["id"], f"{label}.id")
    _nullable_sha(binding["content_sha256"], f"{label}.content_sha256")
    if not _bool(binding["required_before_execution"], f"{label}.required_before_execution"):
        raise PreflightError(f"{label} must be required before execution")
    return binding


def _validate_manifest(manifest: dict[str, Any]) -> None:
    _exact_fields(
        manifest,
        {
            "schema",
            "experiment_id",
            "successor_id",
            "lifecycle",
            "protocol_binding",
            "candidate_binding",
            "profile_binding",
            "semantic_budget_binding",
            "validation_binding",
            "corpus_binding",
            "boundary_fixtures",
            "activation_bindings",
            "rules",
            "execution_policy",
            "result_binding",
            "receipt_binding",
            "content_references",
        },
        "manifest",
    )
    if manifest["schema"] != SCHEMA or manifest["experiment_id"] != EXPERIMENT_ID:
        raise PreflightError("manifest schema or experiment identity differs")
    successor_id = _id(manifest["successor_id"], "successor_id")
    if successor_id != "exp-0002-phase2-authored-conflict-draft-001":
        raise PreflightError("successor_id differs from this draft package")
    if manifest["lifecycle"] != "draft":
        raise PreflightError("successor preregistration must remain lifecycle=draft")

    protocol = _validate_identity_binding(manifest["protocol_binding"], "protocol_binding", "draft")
    if protocol["id"] != PROTOCOL_DRAFT_ID or protocol["content_sha256"] is not None:
        raise PreflightError("protocol_binding must use the exact unbound-content draft identity")

    candidate = _validate_identity_binding(manifest["candidate_binding"], "candidate_binding", "unbound")
    if candidate["id"] is not None or candidate["content_sha256"] is not None:
        raise PreflightError("candidate_binding must remain identity-unbound")

    profile = _object(manifest["profile_binding"], "profile_binding")
    _exact_fields(
        profile,
        {
            "state",
            "kind",
            "id",
            "definition_sha256",
            "source",
            "separate_from_expected_snapshot",
            "required_before_held_out",
        },
        "profile_binding",
    )
    if profile["state"] != "unbound" or profile["kind"] != "authored-conflict":
        raise PreflightError("profile_binding must remain an unbound authored-conflict binding")
    _nullable_string(profile["id"], "profile_binding.id")
    _nullable_sha(profile["definition_sha256"], "profile_binding.definition_sha256")
    if profile["id"] is not None or profile["definition_sha256"] is not None:
        raise PreflightError("profile_binding must remain identity-unbound")
    if profile["source"] != "bounded-successor-evidence-only":
        raise PreflightError("profile_binding source must be bounded successor evidence")
    if not _bool(profile["separate_from_expected_snapshot"], "profile_binding.separate_from_expected_snapshot"):
        raise PreflightError("authored-conflict profile must be separate from expected-snapshot profiles")
    if not _bool(profile["required_before_held_out"], "profile_binding.required_before_held_out"):
        raise PreflightError("authored-conflict profile must bind before held-out execution")

    for name in ("semantic_budget_binding", "validation_binding"):
        binding = _object(manifest[name], name)
        _exact_fields(binding, {"state", "values", "required_before_held_out"}, name)
        if binding["state"] != "unbound" or binding["values"] is not None:
            raise PreflightError(f"{name} must remain unbound with null values")
        if not _bool(binding["required_before_held_out"], f"{name}.required_before_held_out"):
            raise PreflightError(f"{name} must bind before held-out execution")

    corpus = _object(manifest["corpus_binding"], "corpus_binding")
    _exact_fields(corpus, {"state", "role_order", "roles", "required_before_held_out"}, "corpus_binding")
    if corpus["state"] != "unbound":
        raise PreflightError("corpus_binding.state must remain unbound")
    role_order = _list(corpus["role_order"], "corpus_binding.role_order")
    if tuple(role_order) != ROLES:
        raise PreflightError("corpus role order must be development, held-out, adversarial")
    if not _bool(corpus["required_before_held_out"], "corpus_binding.required_before_held_out"):
        raise PreflightError("corpus identities must bind before held-out execution")
    roles = _list(corpus["roles"], "corpus_binding.roles")
    if len(roles) != len(ROLES):
        raise PreflightError("corpus_binding.roles must contain exactly three roles")
    for index, (role, value) in enumerate(zip(ROLES, roles)):
        entry = _object(value, f"corpus_binding.roles[{index}]")
        _exact_fields(
            entry,
            {"role", "state", "id", "path", "sha256", "execution_order", "tuning_allowed", "held_out_blind"},
            f"corpus_binding.roles[{index}]",
        )
        if entry["role"] != role or entry["state"] != "unbound" or entry["execution_order"] != index + 1:
            raise PreflightError("corpus roles must be ordered and remain unbound in the draft")
        _nullable_string(entry["id"], f"corpus role {role}.id")
        _nullable_string(entry["path"], f"corpus role {role}.path")
        _nullable_sha(entry["sha256"], f"corpus role {role}.sha256")
        if entry["id"] is not None or entry["path"] is not None or entry["sha256"] is not None:
            raise PreflightError(f"corpus role {role} must remain content-unbound")
        _bool(entry["tuning_allowed"], f"corpus role {role}.tuning_allowed")
        _bool(entry["held_out_blind"], f"corpus role {role}.held_out_blind")
        if entry["tuning_allowed"] != (role == "development") or entry["held_out_blind"] is not False:
            raise PreflightError(f"corpus role {role} metadata conflicts with the frozen lifecycle rule")

    fixtures = _list(manifest["boundary_fixtures"], "boundary_fixtures")
    if len(fixtures) != len(FIXTURE_DEFINITIONS):
        raise PreflightError("boundary_fixtures must contain exactly the five required roles")
    for index, (value, expected) in enumerate(zip(fixtures, FIXTURE_DEFINITIONS)):
        fixture = _object(value, f"boundary_fixtures[{index}]")
        _exact_fields(
            fixture,
            {"id", "request_profile", "expected_outcome", "expected_diagnostic", "graph_constraints", "state", "path", "sha256"},
            f"boundary_fixtures[{index}]",
        )
        constraints = _list(fixture["graph_constraints"], f"boundary_fixtures[{index}].graph_constraints")
        actual = (
            fixture["id"],
            fixture["request_profile"],
            fixture["expected_outcome"],
            fixture["expected_diagnostic"],
            tuple(constraints),
        )
        if actual != expected:
            raise PreflightError(f"boundary fixture {index} differs from the exact DR-0008 Revision 14 definition")
        _id(fixture["id"], f"boundary_fixtures[{index}].id")
        if fixture["state"] != "unbound" or fixture["path"] is not None or fixture["sha256"] is not None:
            raise PreflightError(f"boundary fixture {fixture['id']} must remain content-unbound")

    activation = _object(manifest["activation_bindings"], "activation_bindings")
    _exact_fields(
        activation,
        {"state", "resolver_source", "resolver_binding", "complete_build_request", "required_before_execution"},
        "activation_bindings",
    )
    if activation["state"] != "unbound":
        raise PreflightError("activation_bindings.state must remain unbound")
    if not _bool(activation["required_before_execution"], "activation_bindings.required_before_execution"):
        raise PreflightError("activation bindings must be required before execution")
    for key in ("resolver_source", "resolver_binding", "complete_build_request"):
        if activation[key] is not None:
            raise PreflightError(f"activation_bindings.{key} must remain null in this draft")

    rules = _object(manifest["rules"], "rules")
    _exact_fields(
        rules,
        {
            "comparison_target",
            "comparison_profile",
            "held_out_tuning",
            "failure_or_inconclusive",
            "outcomes",
            "mismatch_policy",
            "admitted_conflict_policy",
            "evidence_lineage",
            "execution_gate",
        },
        "rules",
    )
    expected_rules = {
        "comparison_target": "authored-root-local-vs-attachment-derived",
        "comparison_profile": "one-explicit-separately-content-bound-authored-conflict-profile",
        "held_out_tuning": "prohibited",
        "failure_or_inconclusive": "new-candidate-evaluation",
        "mismatch_policy": "fail-closed",
        "admitted_conflict_policy": "no-successful-snapshot",
        "execution_gate": "complete-registration-required",
    }
    for key, expected in expected_rules.items():
        if rules[key] != expected:
            raise PreflightError(f"rules.{key} differs from the decided successor mechanics")
    outcomes = _list(rules["outcomes"], "rules.outcomes")
    lineage = _list(rules["evidence_lineage"], "rules.evidence_lineage")
    if tuple(outcomes) != ("agree", "conflict", "skipped", "incomplete", "unsupported"):
        raise PreflightError("rules.outcomes must preserve agree/conflict/skipped and incomplete/unsupported")
    if tuple(lineage) != ("protocol", "candidate", "corpora", "result", "receipt"):
        raise PreflightError("rules.evidence_lineage must bind protocol/candidate/corpora/result/receipt")

    for name in ("result_binding", "receipt_binding"):
        binding = _validate_identity_binding(manifest[name], name, "unbound")
        if binding["id"] is not None or binding["content_sha256"] is not None:
            raise PreflightError(f"{name} must remain identity-unbound")

    policy = _object(manifest["execution_policy"], "execution_policy")
    _exact_fields(policy, {"preflight_only_supported", "execution_permitted", "result_or_receipt_created"}, "execution_policy")
    if not _bool(policy["preflight_only_supported"], "execution_policy.preflight_only_supported"):
        raise PreflightError("preflight-only must be supported")
    if _bool(policy["execution_permitted"], "execution_policy.execution_permitted"):
        raise PreflightError("this package must remain non-executing")
    if _bool(policy["result_or_receipt_created"], "execution_policy.result_or_receipt_created"):
        raise PreflightError("this package must not create a result or receipt")

    references = _list(manifest["content_references"], "content_references")
    if len(references) != MAX_CONTENT_REFERENCES:
        raise PreflightError("content_references must contain exactly the three canonical references")
    expected_total = 0
    for index, (value, expected_triple) in enumerate(zip(references, CANONICAL_REFERENCE_TRIPLES)):
        reference = _object(value, f"content_references[{index}]")
        _exact_fields(reference, {"id", "path", "role", "expected_sha256", "expected_bytes"}, f"content_references[{index}]")
        actual_triple = (reference["id"], reference["path"], reference["role"])
        if actual_triple != expected_triple:
            raise PreflightError("content reference identity/path/role set differs from the canonical draft")
        _id(reference["id"], f"content_references[{index}].id")
        if not isinstance(reference["expected_sha256"], str) or not SHA256_RE.fullmatch(reference["expected_sha256"]):
            raise PreflightError(f"content reference {reference['id']} expected_sha256 is invalid")
        expected_bytes = reference["expected_bytes"]
        if not isinstance(expected_bytes, int) or isinstance(expected_bytes, bool) or not 0 <= expected_bytes <= MAX_REFERENCE_BYTES:
            raise PreflightError(f"content reference {reference['id']} expected_bytes exceeds the per-file bound")
        expected_total += expected_bytes
    if expected_total > MAX_AGGREGATE_REFERENCE_BYTES:
        raise PreflightError("declared content references exceed the aggregate byte bound")


def _repo_root(manifest_path: Path) -> Path:
    for parent in (manifest_path.parent, *manifest_path.parents):
        if (parent / ".git").exists():
            return parent.absolute()
    raise PreflightError("cannot locate repository root from manifest path")


def _reference_path_without_symlinks(root: Path, path_text: str) -> Path:
    relative = Path(path_text)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise PreflightError(f"content reference must be a normalized repository-relative path: {path_text}")
    current = root
    try:
        for part in relative.parts:
            current = current / part
            component = os.lstat(current)
            if stat.S_ISLNK(component.st_mode):
                raise PreflightError(f"content reference contains a symlink component: {path_text}")
    except PreflightError:
        raise
    except OSError as exc:
        raise PreflightError(f"cannot inspect content reference {path_text}: {exc}") from exc
    return current


def _stat_signature(value: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _stream_identity(root: Path, reference: Mapping[str, Any]) -> dict[str, Any]:
    path_text = str(reference["path"])
    path = _reference_path_without_symlinks(root, path_text)
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = -1
    digest = hashlib.sha256()
    size = 0
    try:
        path_before = os.lstat(path)
        descriptor = os.open(path, flags)
        opened_before = os.fstat(descriptor)
        if not stat.S_ISREG(opened_before.st_mode):
            raise PreflightError(f"content reference is not a regular file: {path_text}")
        if (path_before.st_dev, path_before.st_ino) != (opened_before.st_dev, opened_before.st_ino):
            raise PreflightError(f"content reference changed while opening: {path_text}")
        with os.fdopen(descriptor, "rb", closefd=True) as handle:
            descriptor = -1
            while chunk := handle.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_REFERENCE_BYTES:
                    raise PreflightError(f"content reference exceeds {MAX_REFERENCE_BYTES} bytes: {path_text}")
                digest.update(chunk)
            opened_after = os.fstat(handle.fileno())
        path_after = os.lstat(path)
    except PreflightError:
        raise
    except OSError as exc:
        raise PreflightError(f"cannot safely hash content reference {path_text}: {exc}") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if _stat_signature(opened_before) != _stat_signature(opened_after):
        raise PreflightError(f"content reference changed while reading: {path_text}")
    if (path_after.st_dev, path_after.st_ino) != (opened_after.st_dev, opened_after.st_ino):
        raise PreflightError(f"content reference path changed while reading: {path_text}")
    actual_sha = digest.hexdigest()
    if size != reference["expected_bytes"] or actual_sha != reference["expected_sha256"]:
        raise PreflightError(
            f"content reference changed: {path_text} "
            f"(expected {reference['expected_bytes']} bytes/{reference['expected_sha256']}, "
            f"found {size} bytes/{actual_sha})"
        )
    return {
        "id": reference["id"],
        "path": path_text,
        "role": reference["role"],
        "bytes": size,
        "sha256": actual_sha,
    }


def build_plan(manifest_path: Path) -> dict[str, Any]:
    manifest_path = manifest_path.absolute()
    manifest, manifest_bytes = _parse_json(manifest_path)
    _validate_manifest(manifest)
    root = _repo_root(manifest_path)
    try:
        manifest_relative = manifest_path.relative_to(root).as_posix()
    except ValueError as exc:
        raise PreflightError("manifest must reside within the repository") from exc
    identities: list[dict[str, Any]] = []
    aggregate_size = 0
    for reference in manifest["content_references"]:
        identity = _stream_identity(root, reference)
        aggregate_size += identity["bytes"]
        if aggregate_size > MAX_AGGREGATE_REFERENCE_BYTES:
            raise PreflightError("content references exceed the aggregate byte bound")
        identities.append(identity)
    diagnostics = [
        {"code": "profile-unbound", "severity": "gated", "message": "authored-conflict profile identity and constants remain unbound"},
        {"code": "corpus-unbound", "severity": "gated", "message": "development, held-out, and adversarial corpus identities remain unbound"},
        {"code": "activation-unbound", "severity": "gated", "message": "resolver/source, resolver, and complete-build activation bindings remain unbound"},
    ]
    return {
        "schema": "ck.exp-0002.r3-authored-conflict-preflight-plan-1",
        "experiment_id": EXPERIMENT_ID,
        "successor_id": manifest["successor_id"],
        "protocol_identity": manifest["protocol_binding"],
        "lifecycle": manifest["lifecycle"],
        "profile_binding": manifest["profile_binding"],
        "corpus_roles": manifest["corpus_binding"],
        "boundary_fixture_roles": manifest["boundary_fixtures"],
        "candidate_binding": manifest["candidate_binding"],
        "semantic_budget_binding": manifest["semantic_budget_binding"],
        "validation_binding": manifest["validation_binding"],
        "activation_bindings": manifest["activation_bindings"],
        "result_binding": manifest["result_binding"],
        "receipt_binding": manifest["receipt_binding"],
        "declared_file_identities": identities,
        "manifest_identity": {
            "path": manifest_relative,
            "sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        },
        "filesystem_scope": "controlled-local-change-detection-not-adversarial-filesystem-proof",
        "diagnostics": diagnostics,
        "execution_permitted": False,
        "result_or_receipt_created": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate and print the non-executing EXP-0002 authored-conflict successor preflight plan."
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help="draft preregistration manifest")
    parser.add_argument("--preflight-only", action="store_true", help="validate and print a plan; never execute or create evidence")
    parser.add_argument("--execute", action="store_true", help="rejected: this package has no execution path")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.execute:
        parser.error("execution is intentionally unavailable; this package is preflight-only")
    try:
        plan = build_plan(args.manifest)
    except (OSError, PreflightError, RecursionError, TypeError, ValueError) as exc:
        print(f"preflight failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(plan, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

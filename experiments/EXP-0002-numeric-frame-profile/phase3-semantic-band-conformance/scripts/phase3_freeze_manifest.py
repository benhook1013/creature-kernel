#!/usr/bin/env python3
"""Generate and validate the execution-disabled Phase 3 freeze manifest.

The freeze binds repository inputs and the *artifact build contract*.  It does
not launch the candidate, capture a run, or grant Gate B authorization.  Build
receipts are the only narrow finalization input: once two already-created,
validated receipts are placed under ``manifests/build-receipts/``, this module
records their durable file identities and the binary identities they report.
The receipt files, rather than an ignored binary, are what ordinary checks
re-read later.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import importlib.util
import json
import os
import re
import stat
import struct
import subprocess
import sys
import tempfile
import types
from pathlib import Path
from typing import Any, Mapping


REPO = Path(__file__).resolve().parents[4]
PACKAGE = REPO / "experiments/EXP-0002-numeric-frame-profile/phase3-semantic-band-conformance"
GIT_EXECUTABLE = "/usr/bin/git"
# Freeze-time Git reads are deliberately independent of the caller's ambient
# configuration.  Keep this environment closed: no inherited locale, global
# or system config, home/XDG config discovery, or optional lock behaviour.
GIT_ENV = {
    "LANG": "C",
    "LC_ALL": "C",
    "LC_CTYPE": "C",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_SYSTEM": "/dev/null",
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "HOME": "/nonexistent",
    "XDG_CONFIG_HOME": "/nonexistent",
    "XDG_CACHE_HOME": "/nonexistent",
    "GIT_OPTIONAL_LOCKS": "0",
}
PACKAGE_REL = "experiments/EXP-0002-numeric-frame-profile/phase3-semantic-band-conformance"
MANIFEST_REL = "manifests/freeze-manifest.json"
MANIFEST = PACKAGE / MANIFEST_REL
CANDIDATE_REL = "experiments/EXP-0002-numeric-frame-profile/phase2-authored-conflict/candidate"
CANDIDATE_MANIFEST_REL = f"{CANDIDATE_REL}/Cargo.toml"
CANDIDATE_LOCK_REL = f"{CANDIDATE_REL}/Cargo.lock"
FIXTURE_REL = "examples/body-documents/stylized-digitigrade-biped.json"
WORKFLOW_REL = ".github/workflows/phase3-gate-b-native-build.yml"
RECEIPT_DIR_REL = "manifests/build-receipts"
PHASE_ID = "exp-0002-phase3-semantic-band-conformance-001"
EXPERIMENT_ID = "EXP-0002"
CANDIDATE_PROFILE_ID = "ck.provisional-r3-authored-conflict.semantic-band-1"
EXPECTED_CANDIDATE_SOURCE_COMMIT = "647eab5297adca1998764904cce98eca154738e4"
EXPECTED_V1_MANIFEST_SHA256 = "122b0a88bf553e95a887acebfe436d95218389e339ea5aa1f3c85d0f5186fef3"
EXPECTED_V2_MANIFEST_SHA256 = "d7365e99945cb2e57cd6bac45bac241fc032dc1312cda3a94cfdba14cd17933a"
EXPECTED_V2_EXECUTION_TOOL_SOURCE_COMMIT = "9dca58a84072582db34045b8eac98d6e86d3d5ae"
# This is the recorded materialization commit for the current v2 package.  A
# v3 successor requires callers to supply the new materialization commit (or
# an explicit full-SHA fixture while the new E/M commits are not yet present).
EXPECTED_V2_MATERIALIZATION_COMMIT = "cc1531c2e8efe40f8a4896d11b10973147c5636b"
INHERITED_V1_HASH_DOMAIN = b"ck.exp-0002.phase3.freeze-manifest.inherited-v1.v1\0"
EXPECTED_INHERITED_V1_SHA256 = "4f9bde8be337c49d6cc36162b38f21b1a21c6044160b5a444c31e3d36068b70f"
V1_SCHEMA = "ck.exp-0002.phase3.freeze-manifest-1"
V1_HASH_DOMAIN = b"ck.exp-0002.phase3.freeze-manifest.v1\0"
SCHEMA = "ck.exp-0002.phase3.freeze-manifest-2"
HASH_DOMAIN = b"ck.exp-0002.phase3.freeze-manifest.v2\0"
V3_SCHEMA = "ck.exp-0002.phase3.freeze-manifest-3"
V3_HASH_DOMAIN = b"ck.exp-0002.phase3.freeze-manifest.v3\0"
V4_SCHEMA = "ck.exp-0002.phase3.freeze-manifest-4"
V4_HASH_DOMAIN = b"ck.exp-0002.phase3.freeze-manifest.v4\0"
V5_SCHEMA = "ck.exp-0002.phase3.freeze-manifest-5"
V5_HASH_DOMAIN = b"ck.exp-0002.phase3.freeze-manifest.v5\0"
EXPECTED_V3_MANIFEST_SHA256 = "faafe7680fcc3509a245dde6759396a1391e02c40891128ca44d007726adef85"
EXPECTED_V4_MANIFEST_SHA256 = "092399ed48818b4e6bcf75db12fd6c022fdcbd70d60866eb9f4ddedf48864c72"
# The v3 manifest is the immutable predecessor for the runtime-bound v4
# successor.  Keep these values explicit: a pure v4 validator must be able to
# authenticate the predecessor lineage without reading a moving repository.
EXPECTED_V3_EXECUTION_TOOL_SOURCE_COMMIT = "762b04b8db3397cb1885d94236ad5d47cb321830"
EXPECTED_V3_MATERIALIZATION_COMMIT = "762b04b8db3397cb1885d94236ad5d47cb321830"
EXPECTED_V4_EXECUTION_TOOL_SOURCE_COMMIT = "48bd077d659a0d2fe6d672a33438b2ac3c85f126"
EXPECTED_V4_MATERIALIZATION_COMMIT = "48bd077d659a0d2fe6d672a33438b2ac3c85f126"
CURRENT_SCHEMA = V5_SCHEMA
V2_SCHEMA = SCHEMA
PHASE3_PATH = "scripts/phase3_freeze_manifest.py"
TARGET = "x86_64-unknown-linux-gnu"
TOOLCHAIN = "1.97.1"
BINARY_NAME = "exp-0002-r3-authored-conflict-candidate"

# These are source-level invocation facts, not observations of a host.  The v4
# successor selects CPython 3.13.15 for both selectors so the wrapper and
# oracle execute with identical semantics.  The launch-record argument is a
# shape placeholder; the launcher authenticates the concrete path separately.
PYTHON_RUNTIME_CONTRACT_SCHEMA = "ck.exp-0002.phase3.python-runtime-contract-1"
PYTHON_RUNTIME_CONTRACT_V2_SCHEMA = "ck.exp-0002.phase3.python-runtime-contract-2"
PYTHON_RUNTIME_INVOCATION = [
    "python3.13", "-I", "scripts/phase3_exact_attempt_launcher.py", "--launch-record", "<launch-record>",
]
PYTHON_RUNTIME_MODULE_LOADING = "explicit-sibling-file-loading-under-isolated-mode"
PYTHON_RUNTIME_ENTRYPOINT = "phase3_exact_attempt_launcher.main->phase3_exact_attempt.run_exact_attempt"
PYTHON_RUNTIME_VERSION = "3.13.15"
PYTHON_RUNTIME_KEYS = {
    "selector", "implementation", "version", "invocation", "module_loading", "entrypoint",
}
PYTHON_RUNTIME_V2_KEYS = {
    "selector", "implementation", "version", "interpreter", "interpreter_identity", "invocation",
    "module_loading", "entrypoint", "attestation_identity", "external_tools",
}
RUNTIME_ATTESTATION_SCHEMA = "ck.exp-0002.phase3.python-runtime-attestation-1"
RUNTIME_ATTESTATION_PATHS = {
    "wsl2-x86_64": "manifests/runtime-attestations/wsl.json",
    "ubuntu-24.04-x86_64": "manifests/runtime-attestations/native.json",
}
RUNTIME_PROBE_PATH = "scripts/phase3_python_runtime_probe.py"

RUNTIME_TOOLS = (
    "scripts/phase3_common.py",
    "scripts/phase3_oracle.py",
    "scripts/phase3_scorer.py",
    "scripts/phase3_runner.py",
    "scripts/phase3_receipt.py",
    "scripts/phase3_materialized_adapter.py",
    "scripts/phase3_evidence_contract.py",
    "scripts/phase3_gate_b_preflight.py",
)
EXACT_RUNTIME_TOOLS = (
    "scripts/phase3_exact_adjudicator.py",
    "scripts/phase3_exact_authority.py",
    "scripts/phase3_exact_custody.py",
    "scripts/phase3_exact_fp_observer.py",
    "scripts/phase3_exact_publication.py",
    "scripts/phase3_exact_transport.py",
    "scripts/phase3_exact_attempt.py",
    "scripts/phase3_exact_attempt_launcher.py",
)
# v1–v3 are immutable predecessor shapes. Their exact-runtime closure did not
# yet contain the launcher; only v4 binds the new list above.
LEGACY_EXACT_RUNTIME_TOOLS = EXACT_RUNTIME_TOOLS[:-1]
# These are the exact provenance-producing tools.  Keep this list closed:
# adding a helper changes what the freeze means and therefore needs an explicit
# update to the manifest contract and its tests.
PROVENANCE_TOOLS = (
    "scripts/generate_phase3.py",
    "scripts/check_candidate_prebinding.py",
    "scripts/phase3_build_receipt.py",
    PHASE3_PATH,
)
V5_PROVENANCE_TOOLS = (*PROVENANCE_TOOLS, RUNTIME_PROBE_PATH)
EXPERIMENT_CLOSURE_TOOLS = ("scripts/phase3_experiment_closure.py",)
INHERITED_SUCCESSOR_FIELDS = (
    "candidate_source_commit", "status", "lifecycle", "execution_permitted",
    "binding", "protocol", "raw_inputs", "repository_inputs", "candidate_closure",
    "build", "platform", "binaries", "readiness", "attempts",
)
PACKAGE_INPUTS = (
    "preregistration.json",
    "manifests/artifact-manifest.json",
    "manifests/recipe-manifest.json",
    "corpora/controls.jsonl",
    "corpora/development.jsonl",
    "corpora/held-out.jsonl",
    "sqrt-vectors.json",
)
RELEVANT_PACKAGE_FILES = frozenset((*PACKAGE_INPUTS, MANIFEST_REL, *RUNTIME_TOOLS, *EXACT_RUNTIME_TOOLS, *PROVENANCE_TOOLS, RUNTIME_PROBE_PATH))
SELECTORS = ("wsl2-x86_64", "ubuntu-24.04-x86_64")
ROLE_FOR_SELECTOR = {"wsl2-x86_64": "wsl", "ubuntu-24.04-x86_64": "native"}
RECEIPT_PATHS = {
    "wsl2-x86_64": f"{RECEIPT_DIR_REL}/wsl.json",
    "ubuntu-24.04-x86_64": f"{RECEIPT_DIR_REL}/native.json",
}
SELECTOR_DETAILS = {
    "wsl2-x86_64": {
        "family": "WSL2 x86_64 GNU/Linux",
        "filesystem": "Linux filesystem under /home; repository is not /mnt/c",
        "runner": "Ben-controlled WSL2 shell",
        "workflow": "local WSL2 execution after separate authorization",
    },
    "ubuntu-24.04-x86_64": {
        "family": "Ubuntu 24.04 x86_64",
        "filesystem": "native Linux filesystem",
        "runner": "controlled native Ubuntu 24.04 x86_64 runner",
        "workflow": "native dispatch after separate authorization",
    },
}
REQUEST_FIELDS = [
    "protocol_id", "request_id", "operation", "resource_profile", "source",
    "tolerances", "providers",
]
RESPONSE_PROTOCOL = "ck.exp-0002.r3-authored-conflict-candidate-response-1"
REQUEST_PROTOCOL = "ck.exp-0002.r3-authored-conflict-candidate-request-1"
MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_RECEIPT_BYTES = 128 * 1024
MAX_MANIFEST_BYTES = 2 * 1024 * 1024
SHA256_HEX = set("0123456789abcdef")
FULL_SHA_HEX = SHA256_HEX
ACTION_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
ENV_POLICY = {
    "mode": "sanitized-env-i",
    "ambient": "excluded",
    "variables": {
        "PATH": "<tool-path>",
        "HOME": "<build-home>",
        "CARGO_HOME": "<cargo-home>",
        "RUSTUP_HOME": "<rustup-home>",
        "CARGO_NET_OFFLINE": "true",
        "CARGO_TARGET_DIR": "<fresh-target-dir>",
        "TMPDIR": "<runner-temp>",
    },
}
RECEIPT_DEPENDENCY_FIELDS = ["schema", "algorithm", "sha256", "raw_sha256", "bytes", "packages", "nodes"]
RECEIPT_VENDOR_FIELDS = ["role_path", "algorithm", "files", "bytes", "path_sha256", "content_sha256"]
PLATFORM_OBSERVATION_FIELDS = ["stability", "runner_os", "runner_arch", "image_os", "image_version", "kernel", "sanitized_environment_keys"]


class FreezeManifestError(ValueError):
    """Stable fail-closed error for freeze generation and validation."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = str(code)
        self.detail = str(detail).replace("\x00", "?").replace("\n", " ").replace("\r", "")[:256]
        super().__init__(f"{self.code}: {self.detail}" if self.detail else self.code)


def _fail(code: str, detail: str) -> None:
    raise FreezeManifestError(code, detail)


def _canonical(value: Any) -> bytes:
    try:
        return (json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise FreezeManifestError("canonical-json", "value cannot be encoded as canonical JSON") from error


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _valid_sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in SHA256_HEX for char in value)


def _valid_commit(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 40 and all(char in FULL_SHA_HEX for char in value)


def _git_run(repo: Path, *arguments: str, **kwargs: Any) -> subprocess.CompletedProcess:
    """Run one read-only Git operation through the fixed executable seam."""
    kwargs.setdefault("check", False)
    kwargs["env"] = dict(GIT_ENV)
    return subprocess.run([GIT_EXECUTABLE, "-C", str(repo), *arguments], **kwargs)


def _git_head(repo: Path) -> str:
    try:
        result = _git_run(
            repo, "rev-parse", "--verify", "HEAD",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except OSError as error:
        raise FreezeManifestError("source-commit", "cannot invoke Git to resolve HEAD") from error
    commit = result.stdout.strip()
    if result.returncode or not _valid_commit(commit):
        _fail("source-commit", "repository HEAD is unavailable or is not a full commit")
    return commit


def _resolve_source_commit(repo: Path, source_commit: str | None) -> str:
    if source_commit is not None:
        if not _valid_commit(source_commit):
            _fail("source-commit", "source commit must be a full lowercase SHA-1")
        return source_commit
    return _git_head(repo)


def _assert_descendant_commit(repo: Path, ancestor: str, descendant: str) -> None:
    if not _valid_commit(ancestor) or not _valid_commit(descendant):
        _fail("execution-tool-commit", "source commits must be full lowercase commit IDs")
    try:
        result = _git_run(
            repo, "merge-base", "--is-ancestor", ancestor, descendant,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as error:
        raise FreezeManifestError("execution-tool-commit", "cannot compare source commits") from error
    if result.returncode != 0:
        _fail("execution-tool-commit", "execution tool commit is not a descendant of the candidate commit")


def _safe_path(root: Path, relative: str) -> Path:
    if not relative or relative.startswith("/") or "\\" in relative:
        _fail("path", f"unsafe relative path {relative!r}")
    parts = relative.split("/")
    if any(part in ("", ".", "..") for part in parts):
        _fail("path", f"unsafe relative path {relative!r}")
    path = root.joinpath(*parts)
    current = root
    for part in parts:
        current = current / part
        try:
            info = current.lstat()
        except OSError as error:
            raise FreezeManifestError("missing-file", relative) from error
        if stat.S_ISLNK(info.st_mode):
            _fail("symlink", f"{relative} contains a symlink")
    return path


def _file_identity(root: Path, relative: str) -> dict[str, Any]:
    path = _safe_path(root, relative)
    try:
        info = path.lstat()
    except OSError as error:
        raise FreezeManifestError("missing-file", relative) from error
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        _fail("file-type", f"{relative} is not a single-link regular file")
    if info.st_size > MAX_FILE_BYTES:
        _fail("file-size", f"{relative} exceeds the bounded identity size")
    raw = path.read_bytes()
    if len(raw) != info.st_size:
        _fail("file-race", f"{relative} changed while reading")
    return {"path": relative, "mode": stat.S_IMODE(info.st_mode), "bytes": len(raw), "sha256": _sha256(raw)}


def _workflow_input(repo: Path) -> dict[str, Any]:
    """Bind the native build workflow bytes and expose only descriptive facts."""
    identity = _file_identity(repo, WORKFLOW_REL)
    raw = _safe_path(repo, WORKFLOW_REL).read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise FreezeManifestError("workflow", "native build workflow is not UTF-8") from error
    runner_match = re.search(r"(?m)^\s*runs-on:\s*([^\s#]+)", text)
    if runner_match is None:
        _fail("workflow", "native build workflow has no runner label")
    action_refs = re.findall(r"(?m)^\s*uses:\s*([^\s#]+)", text)
    for reference in action_refs:
        if "@" not in reference or not ACTION_SHA_RE.fullmatch(reference.rsplit("@", 1)[1]):
            _fail("workflow", "native build workflow action refs must use immutable 40-hex SHAs")
    return {
        "identity": identity,
        "runner_label": runner_match.group(1),
        "pinned_action_refs": action_refs,
    }


def _git_blob_identity(repo: Path, commit: str, relative: str) -> dict[str, Any]:
    """Read one bounded blob and its tree mode from a candidate commit."""
    if not relative or relative.startswith("/") or "\\" in relative or any(part in {"", ".", ".."} for part in relative.split("/")):
        _fail("source-commit", f"unsafe Git source path {relative!r}")
    try:
        tree = _git_run(
            repo, "ls-tree", "-z", commit, "--", relative,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as error:
        raise FreezeManifestError("source-commit", "cannot read candidate Git tree") from error
    records = [record for record in tree.stdout.split(b"\0") if record]
    if tree.returncode or len(records) != 1:
        _fail("source-commit", f"candidate commit does not contain exactly one source blob: {relative}")
    try:
        metadata, path_bytes = records[0].split(b"\t", 1)
        mode_text, kind, object_id = metadata.decode("ascii").split(" ")
        path = path_bytes.decode("utf-8")
        mode = int(mode_text, 8)
    except (UnicodeDecodeError, ValueError) as error:
        raise FreezeManifestError("source-commit", f"malformed Git tree record for {relative}") from error
    if kind != "blob" or path != relative or not stat.S_ISREG(mode):
        _fail("source-commit", f"candidate commit source is not a regular blob: {relative}")
    try:
        blob = _git_run(
            repo, "cat-file", "blob", object_id,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as error:
        raise FreezeManifestError("source-commit", "cannot read candidate Git blob") from error
    if blob.returncode or len(blob.stdout) > MAX_FILE_BYTES:
        _fail("source-commit", f"candidate Git blob is unavailable or oversized: {relative}")
    return {"path": relative, "mode": mode, "bytes": len(blob.stdout), "sha256": _sha256(blob.stdout)}


def _assert_git_identity(repo: Path, commit: str, relative: str, expected: Mapping[str, Any], *, full_mode: bool = False) -> None:
    observed = _git_blob_identity(repo, commit, relative)
    expected_mode = expected.get("mode")
    if not isinstance(expected_mode, int):
        _fail("source-commit", f"frozen source mode is malformed: {relative}")
    if not full_mode:
        expected_mode = stat.S_IFREG | expected_mode
    if {"path": relative, "mode": expected_mode, "bytes": expected.get("bytes"), "sha256": expected.get("sha256")} != observed:
        _fail("source-commit", f"candidate commit bytes differ from frozen identity: {relative}")


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        _fail("import", f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _candidate_entries(repo: Path, package: Path) -> tuple[Any, list[dict[str, Any]]]:
    checker = _load_module(f"phase3_candidate_prebinding_for_freeze_{id(package)}", package / "scripts/check_candidate_prebinding.py")
    # The checker is freshly loaded for this validation path.  Bind both its
    # executable and closed environment to freeze's own seam before invoking
    # any checker operation; ambient sys.modules and PATH are not authorities.
    checker.GIT_EXECUTABLE = GIT_EXECUTABLE
    checker.GIT_ENV = dict(GIT_ENV)
    try:
        checker.check(repo, checker.BASE_COMMIT)
        base_entries = checker.select_base_entries(repo, checker.BASE_COMMIT)
        current = [checker._safe_current_entry(repo, entry) for entry in base_entries]
    except Exception as error:
        raise FreezeManifestError("candidate-closure", str(error)) from error
    entries = [
        {"path": entry.path, "mode": entry.mode, "bytes": len(entry.content), "sha256": _sha256(entry.content)}
        for entry in sorted(current, key=lambda item: item.path.encode("utf-8"))
    ]
    return checker, entries


def _closure_identity(entries: list[dict[str, Any]]) -> dict[str, Any]:
    path_stream = bytearray(b"ck.phase3-candidate-source-build-path-set.v1\0")
    total = 0
    for item in entries:
        encoded = item["path"].encode("utf-8")
        path_stream += len(encoded).to_bytes(4, "big") + encoded + int(item["mode"]).to_bytes(4, "big")
        total += int(item["bytes"])
    return {"count": len(entries), "total_raw_bytes": total, "path_set_sha256": _sha256(bytes(path_stream))}


def _raw_inputs(repo: Path, package: Path) -> list[dict[str, Any]]:
    return [_file_identity(package, item) for item in PACKAGE_INPUTS] + [_file_identity(repo, FIXTURE_REL)]


def _tool_identities(package: Path, paths: tuple[str, ...]) -> list[dict[str, Any]]:
    return [_file_identity(package, path) for path in paths]


def _execution_tool_identities_from_commit(
    repo: Path,
    commit: str,
    paths: tuple[str, ...],
) -> list[dict[str, Any]]:
    """Read one closed tool collection from the committed execution snapshot."""
    if not _valid_commit(commit):
        _fail("execution-tool-commit", "execution tool source commit is not a full commit")
    identities: list[dict[str, Any]] = []
    for path in paths:
        repository_path = f"{PACKAGE_REL}/{path}"
        identity = _git_blob_identity(repo, commit, repository_path)
        identities.append({
            "path": path,
            "mode": stat.S_IMODE(identity["mode"]),
            "bytes": identity["bytes"],
            "sha256": identity["sha256"],
        })
    return identities


def _parse_preregistration(package: Path) -> dict[str, Any]:
    try:
        value = json.loads(_safe_path(package, "preregistration.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FreezeManifestError("preregistration", "preregistration is not JSON") from error
    if value.get("experiment_id") != EXPERIMENT_ID or value.get("phase_id") != PHASE_ID:
        _fail("phase-binding", "preregistration does not use the canonical phase ID")
    if value.get("execution_permitted") is not False:
        _fail("execution-state", "preregistration execution must remain disabled")
    return value


def _dependencies(repo: Path) -> dict[str, Any]:
    lock = _file_identity(repo, CANDIDATE_LOCK_REL)
    return {
        "cargo_lock": lock,
        "dependency_closure_contract": {
            "schema": "ck.exp-0002.phase3.gate-b-cargo-metadata-1",
            "algorithm": "ck.exp-0002.phase3.gate-b-dependency-closure.v1",
            "fields": RECEIPT_DEPENDENCY_FIELDS,
        },
        "vendor_closure_contract": {
            "algorithm": "ck.exp-0002.phase3.gate-b-vendor-closure.v1",
            "fields": RECEIPT_VENDOR_FIELDS,
            "role_path_pattern": "phase3-gate-b-{platform_role}-vendor",
        },
        "cargo_config_contract": {
            "algorithm": "ck.exp-0002.phase3.gate-b-controlled-vendor-config.v1",
            "fields": ["role_path", "algorithm", "sha256", "bytes"],
            "role_path_pattern": "phase3-gate-b-{platform_role}-cargo-config",
        },
        "offline": True,
    }


def _build_recipe() -> dict[str, Any]:
    argv = [
        "cargo", "+1.97.1", "build", "--manifest-path", CANDIDATE_MANIFEST_REL,
        "--target", TARGET, "--target-dir", "<fresh-target-dir>", "--locked", "--offline",
    ]
    return {
        "artifact_build": {
            "argv_template": argv,
            "working_directory": ".",
            "target": TARGET,
            "profile": "dev",
            "environment": ENV_POLICY,
            "binary_role_path_pattern": "phase3-gate-b-{platform_role}-target/{target}/debug/" + BINARY_NAME,
            "vendor_role_path_pattern": "phase3-gate-b-{platform_role}-vendor",
            "forbidden_overrides": [
                "extra argv tokens", "cargo test", "cargo run", "cargo install", "wrapper commands",
                "features", "--release", "ambient CARGO_* configuration", "RUSTFLAGS",
                "CARGO_BUILD_RUSTFLAGS", "target-cpu=native", "network access", "non-fresh target directory",
            ],
        },
        "validation": {"scope": "focused checks are separate from artifact identity and do not authorize execution"},
        "manifest_path": CANDIDATE_MANIFEST_REL,
        "source": "candidate Cargo.toml and Cargo.lock in the candidate closure",
    }


def _toolchain(repo: Path) -> dict[str, Any]:
    return {
        "rust_toolchain_file": "rust-toolchain.toml",
        "rust_toolchain_file_identity": _file_identity(repo, "rust-toolchain.toml"),
        "channel": TOOLCHAIN,
        "profile": "minimal",
        "components": ["rustfmt", "clippy"],
        "rustc": {"release": TOOLCHAIN, "commit_hash": "8bab26f4f68e0e26f0bb7960be334d5b520ea452", "host": TARGET, "llvm": "22.1.6"},
        "cargo": {"release": TOOLCHAIN, "commit_hash": "c980f4866141969fab6254a680546a277789d6f0"},
        "receipt_contract": {
            "rust_toolchain": TOOLCHAIN,
            "rustc_prefix": "rustc 1.97.1",
            "rustc_commit_hash": "8bab26f4f68e0e26f0bb7960be334d5b520ea452",
            "rustc_host": TARGET,
            "rustc_llvm": "22.1.6",
            "cargo_prefix": "cargo 1.97.1",
            "cargo_commit_hash": "c980f4866141969fab6254a680546a277789d6f0",
            "cargo_host": TARGET,
            "python_prefix": "Python 3",
        },
    }


def _platforms() -> dict[str, Any]:
    return {
        "selectors": [{"selector": selector, **SELECTOR_DETAILS[selector], "architecture": "x86_64", "target": TARGET} for selector in SELECTORS],
        "runner_contract": {
            "processes_per_attempt": 3, "roles": ["development", "held-out", "controls"],
            "request_counts": {"development": 8, "held-out": 40, "controls": 9},
            "filesystem_observation": "recorded per attempt outside this manifest",
            "order": "fixed development; held-out; controls; no automatic retry or reordering",
            "build_receipt_platform_observation": {"fields": PLATFORM_OBSERVATION_FIELDS, "stability": "observed-for-this-build-only"},
        },
    }


def _build_python_runtime_contract(
    *,
    runtime_contract: Mapping[str, Any] | None,
    native_python_version: str | None = None,
) -> dict[str, Any]:
    """Authenticate an explicit runtime contract supplied by a fixed workflow.

    This function never probes ``sys`` or invents a patch version.  Both
    selectors must explicitly bind the fixed CPython 3.13.15 release and the
    launcher boundary. ``native_python_version`` is retained only as a
    consistency check for callers migrating from the provisional API.
    """
    if runtime_contract is None:
        _fail("runtime-contract", "v4 requires an authoritative exact_python_runtime_contract input")
    normalized = _validate_python_runtime_contract(runtime_contract)
    if native_python_version is not None and normalized["platforms"]["ubuntu-24.04-x86_64"]["version"] != native_python_version:
        _fail("runtime-contract", "native Python version does not match the supplied runtime contract")
    return normalized


def _load_runtime_contract_json(path: Path) -> dict[str, Any]:
    """Load one canonical, strict JSON runtime-contract mapping from disk."""
    try:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            _fail("runtime-contract", "runtime-contract JSON must be a single-link regular file")
        raw = path.read_bytes()
    except FreezeManifestError:
        raise
    except OSError as error:
        raise FreezeManifestError("runtime-contract", "runtime-contract JSON is unavailable") from error
    if len(raw) > MAX_MANIFEST_BYTES or not raw.endswith(b"\n"):
        _fail("runtime-contract", "runtime-contract JSON is oversized or missing its trailing newline")

    def collect(items: list[tuple[str, Any]]) -> dict[str, Any]:
        keys = [key for key, _ in items]
        if len(keys) != len(set(keys)):
            _fail("runtime-contract", "runtime-contract JSON contains duplicate keys")
        return dict(items)

    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=collect,
            parse_constant=lambda token: _fail("runtime-contract", f"runtime-contract JSON contains {token}"),
        )
    except FreezeManifestError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FreezeManifestError("runtime-contract", "runtime-contract JSON is not strict UTF-8 JSON") from error
    if not isinstance(value, Mapping) or _canonical(value) != raw:
        _fail("runtime-contract", "runtime-contract JSON is not a canonical mapping")
    try:
        if value.get("schema") == PYTHON_RUNTIME_CONTRACT_V2_SCHEMA:
            return _validate_python_runtime_contract_v2(value)
        return _validate_python_runtime_contract(value)
    except FreezeManifestError as error:
        raise FreezeManifestError("runtime-contract", error.detail) from error


_SLOT_KEYS = {"status", "receipt_path", "receipt_bytes", "receipt_sha256", "receipt_self_hash", "binary_identity"}


def _binary_slots(bindings: Mapping[str, Any] | None = None) -> dict[str, Any]:
    bindings = bindings or {}
    slots: dict[str, Any] = {}
    for selector in SELECTORS:
        value = bindings.get(selector)
        if value is None:
            slots[selector] = {"status": "unbound", "receipt_path": None, "receipt_bytes": None, "receipt_sha256": None, "receipt_self_hash": None, "binary_identity": None}
            continue
        if not isinstance(value, Mapping) or set(value) != _SLOT_KEYS:
            _fail("binary-binding", f"binary binding for {selector} is not closed")
        if value["status"] == "unbound":
            if any(value[key] is not None for key in _SLOT_KEYS - {"status"}):
                _fail("binary-binding", f"unbound binary slot for {selector} contains an identity")
            slots[selector] = {"status": "unbound", "receipt_path": None, "receipt_bytes": None, "receipt_sha256": None, "receipt_self_hash": None, "binary_identity": None}
            continue
        if value["status"] != "bound" or not isinstance(value["binary_identity"], Mapping):
            _fail("binary-binding", f"binary binding for {selector} is not bound")
        path = value["receipt_path"]
        if not isinstance(path, str) or not path.startswith(RECEIPT_DIR_REL + "/") or "\\" in path or ".." in path.split("/"):
            _fail("binary-binding", f"receipt path for {selector} is unsafe")
        if type(value["receipt_bytes"]) is not int or value["receipt_bytes"] <= 0:
            _fail("binary-binding", f"receipt bytes for {selector} are invalid")
        for key in ("receipt_sha256", "receipt_self_hash"):
            if not _valid_sha(value[key]):
                _fail("binary-binding", f"{key} for {selector} is invalid")
        identity = value["binary_identity"]
        if set(identity) != {"bytes", "mode", "sha256"} or type(identity["bytes"]) is not int or identity["bytes"] <= 0 or type(identity["mode"]) is not int or not stat.S_ISREG(identity["mode"]) or not _valid_sha(identity["sha256"]):
            _fail("binary-binding", f"binary identity for {selector} is invalid")
        slots[selector] = {
            "status": "bound", "receipt_path": path, "receipt_bytes": value["receipt_bytes"],
            "receipt_sha256": value["receipt_sha256"], "receipt_self_hash": value["receipt_self_hash"],
            "binary_identity": dict(identity),
        }
    states = {slots[selector]["status"] for selector in SELECTORS}
    if states not in ({"unbound"}, {"bound"}):
        _fail("binary-binding", "binary slots must be both unbound or both bound")
    return slots


def _readiness(binaries: Mapping[str, Any]) -> dict[str, Any]:
    missing = [f"{selector} build receipt and binary identity" for selector in SELECTORS if binaries[selector]["status"] != "bound"]
    if not missing:
        missing = []
    return {
        "materialization_state": "frozen" if not missing else "pre-freeze",
        "gate_b_review_requirement": "external current-revision Double review must bind this immutable manifest hash",
        "authorization_boundary": "external Ben authorization is required for exact attempts and native dispatch",
        "execution_permitted": False,
        "freeze_blockers": missing,
    }


def _base_manifest(repo: Path = REPO, package: Path = PACKAGE, *, binaries: Mapping[str, Any] | None = None, source_commit: str | None = None) -> dict[str, Any]:
    if not _valid_commit(source_commit):
        _fail("source-commit", "base manifest requires a full source commit")
    checker, entries = _candidate_entries(repo, package)
    closure = _closure_identity(entries)
    expected = checker.Identity(checker.EXPECTED_COUNT, checker.EXPECTED_BYTES, checker.EXPECTED_PATH_SHA256, checker.EXPECTED_CONTENT_SHA256)
    if closure["count"] != expected.count or closure["total_raw_bytes"] != expected.total_bytes or closure["path_set_sha256"] != expected.path_sha256:
        _fail("candidate-closure", "manifest path closure differs from the prebinding checker")
    closure.update({"content_sha256": expected.content_sha256, "algorithm": "ck.phase3-candidate-source-build-closure.v1", "base_commit": checker.BASE_COMMIT, "entries": entries})
    _parse_preregistration(package)
    binary_slots = _binary_slots(binaries)
    return {
        "schema": V1_SCHEMA,
        "manifest_sha256": None,
        "candidate_source_commit": source_commit,
        "status": "Proposed",
        "lifecycle": "planned",
        "execution_permitted": False,
        "binding": {"experiment_id": EXPERIMENT_ID, "phase_id": PHASE_ID, "candidate_profile_id": CANDIDATE_PROFILE_ID},
        "protocol": {"request_protocol_id": REQUEST_PROTOCOL, "response_protocol_id": RESPONSE_PROTOCOL, "request_fields": REQUEST_FIELDS, "canonical_wire": "strict UTF-8 JSON object, exact seven request fields, canonical bytes are SHA-256 framed by the evidence contract"},
        "raw_inputs": _raw_inputs(repo, package),
        "repository_inputs": {"native_build_workflow": {"path": WORKFLOW_REL, **_workflow_input(repo)}},
        "candidate_closure": closure,
        "runtime_tool_identities": _tool_identities(package, RUNTIME_TOOLS),
        "provenance_tool_identities": _tool_identities(package, PROVENANCE_TOOLS),
        "build": {"recipe": _build_recipe(), "toolchain": _toolchain(repo), "dependencies": _dependencies(repo)},
        "platform": _platforms(),
        "binaries": binary_slots,
        "readiness": _readiness(binary_slots),
        "attempts": "per-attempt observations and Ben authorization are external to this manifest",
        "canonicalization": {"encoding": "UTF-8", "json": "RFC 8259-compatible strict JSON", "sort_keys": True, "separators": [",", ":"], "ensure_ascii": True, "trailing_newline": True, "self_hash_domain": V1_HASH_DOMAIN.decode("ascii").rstrip("\0"), "self_hash_excludes": ["manifest_sha256"], "raw_file_hash": "SHA-256 over exact bytes; no parse/reserialize for raw identities"},
    }


def _validate_candidate_commit_snapshot(repo: Path, package: Path, manifest: Mapping[str, Any]) -> None:
    """Prove frozen source identities existed byte-for-byte at candidate commit."""
    candidate_commit = manifest.get("candidate_source_commit")
    if not _valid_commit(candidate_commit):
        _fail("source-commit", "manifest candidate source commit is not a full commit")
    closure = manifest.get("candidate_closure")
    if not isinstance(closure, Mapping) or not isinstance(closure.get("entries"), list):
        _fail("source-commit", "manifest candidate closure is unavailable")
    entry_paths: set[str] = set()
    for entry in closure["entries"]:
        if not isinstance(entry, Mapping) or not isinstance(entry.get("path"), str):
            _fail("source-commit", "manifest candidate closure entry is malformed")
        entry_paths.add(entry["path"])
        _assert_git_identity(repo, candidate_commit, entry["path"], entry, full_mode=True)
    if CANDIDATE_MANIFEST_REL not in entry_paths or CANDIDATE_LOCK_REL not in entry_paths:
        _fail("source-commit", "candidate closure omits Cargo manifest or lockfile")
    for collection_name in ("raw_inputs", "runtime_tool_identities", "provenance_tool_identities"):
        collection = manifest.get(collection_name)
        if not isinstance(collection, list):
            _fail("source-commit", f"manifest {collection_name} is unavailable")
        for identity in collection:
            if not isinstance(identity, Mapping) or not isinstance(identity.get("path"), str):
                _fail("source-commit", f"manifest {collection_name} entry is malformed")
            relative = identity["path"] if identity["path"] == FIXTURE_REL else f"{PACKAGE_REL}/{identity['path']}"
            _assert_git_identity(repo, candidate_commit, relative, identity)
    repository_inputs = manifest.get("repository_inputs")
    workflow = repository_inputs.get("native_build_workflow") if isinstance(repository_inputs, Mapping) else None
    workflow_identity = workflow.get("identity") if isinstance(workflow, Mapping) else None
    if not isinstance(workflow, Mapping) or not isinstance(workflow_identity, Mapping):
        _fail("source-commit", "manifest native workflow identity is unavailable")
    _assert_git_identity(repo, candidate_commit, WORKFLOW_REL, workflow_identity)
    lock = manifest.get("build", {}).get("dependencies", {}).get("cargo_lock") if isinstance(manifest.get("build"), Mapping) else None
    if not isinstance(lock, Mapping):
        _fail("source-commit", "manifest Cargo.lock identity is unavailable")
    _assert_git_identity(repo, candidate_commit, CANDIDATE_LOCK_REL, lock)
    toolchain = manifest.get("build", {}).get("toolchain") if isinstance(manifest.get("build"), Mapping) else None
    toolchain_identity = toolchain.get("rust_toolchain_file_identity") if isinstance(toolchain, Mapping) else None
    if not isinstance(toolchain_identity, Mapping):
        _fail("source-commit", "manifest rust-toolchain identity is unavailable")
    _assert_git_identity(repo, candidate_commit, "rust-toolchain.toml", toolchain_identity)


def _validate_candidate_build_snapshot(repo: Path, manifest: Mapping[str, Any]) -> None:
    """Validate only candidate/build facts against the immutable candidate C."""
    candidate_commit = manifest.get("candidate_source_commit")
    if candidate_commit != EXPECTED_CANDIDATE_SOURCE_COMMIT:
        _fail("source-commit", "successor does not retain the fixed candidate source commit")
    closure = manifest.get("candidate_closure")
    if not isinstance(closure, Mapping) or not isinstance(closure.get("entries"), list):
        _fail("source-commit", "manifest candidate closure is unavailable")
    entry_paths: set[str] = set()
    for entry in closure["entries"]:
        if not isinstance(entry, Mapping) or not isinstance(entry.get("path"), str):
            _fail("source-commit", "manifest candidate closure entry is malformed")
        entry_paths.add(entry["path"])
        _assert_git_identity(repo, candidate_commit, entry["path"], entry, full_mode=True)
    if CANDIDATE_MANIFEST_REL not in entry_paths or CANDIDATE_LOCK_REL not in entry_paths:
        _fail("source-commit", "candidate closure omits Cargo manifest or lockfile")
    raw_inputs = manifest.get("raw_inputs")
    if not isinstance(raw_inputs, list):
        _fail("source-commit", "manifest raw inputs are unavailable")
    for identity in raw_inputs:
        if not isinstance(identity, Mapping) or not isinstance(identity.get("path"), str):
            _fail("source-commit", "manifest raw input entry is malformed")
        relative = identity["path"] if identity["path"] == FIXTURE_REL else f"{PACKAGE_REL}/{identity['path']}"
        _assert_git_identity(repo, candidate_commit, relative, identity)
    repository_inputs = manifest.get("repository_inputs")
    workflow = repository_inputs.get("native_build_workflow") if isinstance(repository_inputs, Mapping) else None
    workflow_identity = workflow.get("identity") if isinstance(workflow, Mapping) else None
    if not isinstance(workflow_identity, Mapping):
        _fail("source-commit", "manifest native workflow identity is unavailable")
    _assert_git_identity(repo, candidate_commit, WORKFLOW_REL, workflow_identity)
    dependencies = manifest.get("build", {}).get("dependencies") if isinstance(manifest.get("build"), Mapping) else None
    lock = dependencies.get("cargo_lock") if isinstance(dependencies, Mapping) else None
    if not isinstance(lock, Mapping):
        _fail("source-commit", "manifest Cargo.lock identity is unavailable")
    _assert_git_identity(repo, candidate_commit, CANDIDATE_LOCK_REL, lock)
    toolchain = manifest.get("build", {}).get("toolchain") if isinstance(manifest.get("build"), Mapping) else None
    toolchain_identity = toolchain.get("rust_toolchain_file_identity") if isinstance(toolchain, Mapping) else None
    if not isinstance(toolchain_identity, Mapping):
        _fail("source-commit", "manifest rust-toolchain identity is unavailable")
    _assert_git_identity(repo, candidate_commit, "rust-toolchain.toml", toolchain_identity)


def _validate_execution_commit_snapshot(repo: Path, package: Path, manifest: Mapping[str, Any]) -> None:
    """Cross-bind all current execution/provenance tools to committed snapshot E."""
    commit = manifest.get("execution_tool_source_commit")
    if not _valid_commit(commit):
        _fail("execution-tool-commit", "execution tool source commit is invalid")
    _assert_descendant_commit(repo, manifest.get("candidate_source_commit"), commit)
    exact_paths = EXACT_RUNTIME_TOOLS if manifest.get("schema") in {V4_SCHEMA, V5_SCHEMA} else LEGACY_EXACT_RUNTIME_TOOLS
    provenance_paths = V5_PROVENANCE_TOOLS if manifest.get("schema") == V5_SCHEMA else PROVENANCE_TOOLS
    for field, paths in (
        ("runtime_tool_identities", RUNTIME_TOOLS),
        ("exact_runtime_tool_identities", exact_paths),
        ("provenance_tool_identities", provenance_paths),
    ):
        expected = _execution_tool_identities_from_commit(repo, commit, paths)
        if manifest.get(field) != expected:
            _fail("execution-tool-commit", f"{field} differs from committed execution snapshot")
        observed = _tool_identities(package, paths)
        if observed != expected:
            _fail("execution-tool-drift", f"current {field} differs from committed execution snapshot")


def _self_hash(value: Mapping[str, Any]) -> str:
    copy = json.loads(json.dumps(value))
    copy.pop("manifest_sha256", None)
    schema = value.get("schema")
    if schema == V1_SCHEMA:
        domain = V1_HASH_DOMAIN
    elif schema == SCHEMA:
        domain = HASH_DOMAIN
    elif schema == V3_SCHEMA:
        domain = V3_HASH_DOMAIN
    elif schema == V4_SCHEMA:
        domain = V4_HASH_DOMAIN
    elif schema == V5_SCHEMA:
        domain = V5_HASH_DOMAIN
    else:
        _fail("manifest-shape", "manifest schema has no self-hash domain")
    return _sha256(domain + _canonical(copy))


def _pure_keys(value: Any, keys: set[str], label: str) -> None:
    if not isinstance(value, Mapping) or set(value) != keys:
        _fail("manifest-shape", f"{label} has missing or unexpected fields")


def _pure_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or value.startswith("/") or "\\" in value or any(part in {"", ".", ".."} for part in value.split("/")):
        _fail("manifest-shape", f"{label} is not a safe relative path")
    return value


def _validate_python_runtime_contract(value: Any) -> dict[str, Any]:
    """Validate the closed, selector-complete exact Python runtime contract."""
    _pure_keys(value, {"schema", "platforms"}, "manifest.exact_python_runtime_contract")
    if value["schema"] != PYTHON_RUNTIME_CONTRACT_SCHEMA:
        _fail("manifest-shape", "Python runtime contract schema is wrong")
    platforms = value["platforms"]
    _pure_keys(platforms, set(SELECTORS), "manifest.exact_python_runtime_contract.platforms")
    normalized: dict[str, Any] = {}
    for selector in SELECTORS:
        selected = platforms[selector]
        _pure_keys(selected, PYTHON_RUNTIME_KEYS, f"manifest.exact_python_runtime_contract.{selector}")
        if selected["selector"] != selector or selected["implementation"] != "CPython":
            _fail("manifest-shape", f"Python runtime selector or implementation is wrong for {selector}")
        if selected["version"] != PYTHON_RUNTIME_VERSION:
            _fail("manifest-shape", f"Python runtime version is not the fixed {PYTHON_RUNTIME_VERSION} contract for {selector}")
        if selected["invocation"] != PYTHON_RUNTIME_INVOCATION:
            _fail("manifest-shape", f"Python invocation is not the frozen contract for {selector}")
        if selected["module_loading"] != PYTHON_RUNTIME_MODULE_LOADING or selected["entrypoint"] != PYTHON_RUNTIME_ENTRYPOINT:
            _fail("manifest-shape", f"Python module-loading or entrypoint contract is wrong for {selector}")
        normalized[selector] = dict(selected)
    return {"schema": value["schema"], "platforms": normalized}


def _runtime_probe_module(package: Path) -> Any:
    path = _safe_path(package, RUNTIME_PROBE_PATH)
    return _load_module(f"phase3_python_runtime_probe_for_freeze_{id(package)}", path)


def _absolute_interpreter_identity(value: Any, label: str) -> dict[str, Any]:
    identity_keys = {"path", "mode", "bytes", "sha256", "uid", "gid", "nlink"}
    if not isinstance(value, Mapping) or set(value) != identity_keys:
        _fail("runtime-contract", f"{label} interpreter identity is not closed")
    path = value["path"]
    if not isinstance(path, str) or not os.path.isabs(path) or "\\" in path or "\x00" in path or any(part in {"", ".", ".."} for part in Path(path).parts[1:]):
        _fail("runtime-contract", f"{label} interpreter path is not absolute and canonical")
    if type(value["mode"]) is not int or value["mode"] < 0 or value["mode"] > 0o7777 or value["mode"] & 0o022 or not stat.S_ISREG(stat.S_IFREG | value["mode"]) or not (value["mode"] & 0o111):
        _fail("runtime-contract", f"{label} interpreter mode is not regular")
    if type(value["bytes"]) is not int or value["bytes"] <= 0 or value["bytes"] > MAX_FILE_BYTES or not _valid_sha(value["sha256"]):
        _fail("runtime-contract", f"{label} interpreter identity is malformed")
    if any(type(value[field]) is not int or value[field] < 0 or value[field] > 0xFFFFFFFF for field in ("uid", "gid")) or value["nlink"] != 1:
        _fail("runtime-contract", f"{label} interpreter identity is malformed")
    return dict(value)


def _validate_runtime_attestation_identity(value: Any, selector: str) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != {"path", "bytes", "sha256", "attestation_sha256"}:
        _fail("runtime-contract", f"runtime attestation identity is not closed for {selector}")
    path = value["path"]
    if path != RUNTIME_ATTESTATION_PATHS[selector] or not isinstance(path, str) or path.startswith("/") or "\\" in path or any(part in {"", ".", ".."} for part in path.split("/")):
        _fail("runtime-contract", f"runtime attestation path is not canonical for {selector}")
    if type(value["bytes"]) is not int or value["bytes"] <= 0 or value["bytes"] > MAX_MANIFEST_BYTES or not _valid_sha(value["sha256"]) or not _valid_sha(value["attestation_sha256"]):
        _fail("runtime-contract", f"runtime attestation identity is malformed for {selector}")
    return dict(value)


def _validate_external_tools(value: Any, selector: str) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != {"git"}:
        _fail("runtime-contract", f"external-tool identity is not closed for {selector}")
    git = value["git"]
    if not isinstance(git, Mapping) or set(git) != {"path", "mode", "bytes", "sha256"}:
        _fail("runtime-contract", f"Git identity is not closed for {selector}")
    path = git["path"]
    if not isinstance(path, str) or not os.path.isabs(path) or "\\" in path or not Path(path).name:
        _fail("runtime-contract", f"Git executable is not an absolute path for {selector}")
    if type(git["mode"]) is not int or not stat.S_ISREG(stat.S_IFREG | git["mode"]) or not (git["mode"] & 0o111) or type(git["bytes"]) is not int or git["bytes"] <= 0 or not _valid_sha(git["sha256"]):
        _fail("runtime-contract", f"Git executable identity is malformed for {selector}")
    return {"git": dict(git)}


def _validate_python_runtime_contract_v2(value: Any) -> dict[str, Any]:
    """Validate v5's selector-complete, content-addressed runtime contract."""
    _pure_keys(value, {"schema", "platforms"}, "manifest.exact_python_runtime_contract")
    if value["schema"] != PYTHON_RUNTIME_CONTRACT_V2_SCHEMA:
        _fail("manifest-shape", "Python runtime contract is not contract-2")
    platforms = value["platforms"]
    _pure_keys(platforms, set(SELECTORS), "manifest.exact_python_runtime_contract.platforms")
    normalized: dict[str, Any] = {}
    for selector in SELECTORS:
        selected = platforms[selector]
        _pure_keys(selected, PYTHON_RUNTIME_V2_KEYS, f"manifest.exact_python_runtime_contract.{selector}")
        if selected["selector"] != selector or selected["implementation"] != "CPython" or selected["version"] != PYTHON_RUNTIME_VERSION:
            _fail("manifest-shape", f"Python runtime selector/version is wrong for {selector}")
        _absolute_interpreter_identity(selected["interpreter_identity"], selector)
        if selected["interpreter_identity"]["path"] != selected["interpreter"] or not isinstance(selected["interpreter"], str) or not os.path.isabs(selected["interpreter"]):
            _fail("manifest-shape", f"Python interpreter path is not bound for {selector}")
        if selected["invocation"] != [selected["interpreter"], "-I", "scripts/phase3_exact_attempt_launcher.py", "--launch-record", "<launch-record>"]:
            _fail("manifest-shape", f"Python invocation is not the canonical absolute launcher argv for {selector}")
        if selected["module_loading"] != PYTHON_RUNTIME_MODULE_LOADING or selected["entrypoint"] != PYTHON_RUNTIME_ENTRYPOINT:
            _fail("manifest-shape", f"Python module-loading/entrypoint contract is wrong for {selector}")
        _validate_runtime_attestation_identity(selected["attestation_identity"], selector)
        _validate_external_tools(selected["external_tools"], selector)
        normalized[selector] = json.loads(json.dumps(selected))
    return {"schema": value["schema"], "platforms": normalized}


def _load_runtime_attestation(package: Path, selector: str, identity: Mapping[str, Any]) -> tuple[dict[str, Any], bytes]:
    relative = identity["path"]
    try:
        path = _safe_path(package, relative)
    except FreezeManifestError as error:
        raise FreezeManifestError("runtime-attestation", f"runtime attestation for {selector} is unavailable") from error
    try:
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o644:
            _fail("runtime-attestation", f"runtime attestation for {selector} is not a single-link file")
        raw = path.read_bytes()
    except OSError as error:
        raise FreezeManifestError("runtime-attestation", f"runtime attestation for {selector} is unavailable") from error
    if len(raw) != identity["bytes"] or _sha256(raw) != identity["sha256"]:
        _fail("runtime-attestation", f"runtime attestation bytes differ from frozen identity for {selector}")
    probe = _runtime_probe_module(package)
    try:
        # Freeze/build validation authenticates the exact canonical sidecar
        # bytes and their declared content identities.  It must not inspect
        # the absolute runtime closure: the other platform is not present and
        # selected-host live drift is an exact-launcher responsibility.
        value = probe.validate_current_attestation(raw, expected_selector=selector, check_files=False)
    except Exception as error:
        raise FreezeManifestError("runtime-attestation", f"runtime attestation for {selector} is invalid") from error
    if value.get("selector") != selector or value.get("schema") != RUNTIME_ATTESTATION_SCHEMA or value.get("attestation_sha256") != identity["attestation_sha256"]:
        _fail("runtime-attestation", f"runtime attestation selector/hash differs for {selector}")
    return value, raw


def _runtime_attestation_contract(package: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    contract = _validate_python_runtime_contract_v2(value)
    for selector in SELECTORS:
        record, _ = _load_runtime_attestation(package, selector, contract["platforms"][selector]["attestation_identity"])
        selected = contract["platforms"][selector]
        # Bind every contract selector to the sidecar's structured facts.  In
        # particular, comparing the complete interpreter identity prevents a
        # same-version replacement executable from passing on path alone.
        for field in ("selector", "implementation", "version", "interpreter", "interpreter_identity", "invocation"):
            if record[field] != selected[field]:
                _fail("runtime-attestation", f"runtime attestation does not bind {field} for {selector}")
    return contract


def _pure_identity(value: Any, label: str, *, full_mode: bool = False) -> None:
    _pure_keys(value, {"path", "mode", "bytes", "sha256"}, label)
    _pure_path(value["path"], f"{label}.path")
    if type(value["mode"]) is not int or not stat.S_ISREG(value["mode"] if full_mode else stat.S_IFREG | value["mode"]):
        _fail("manifest-shape", f"{label}.mode is not a regular-file mode")
    if type(value["bytes"]) is not int or value["bytes"] < 0 or value["bytes"] > MAX_FILE_BYTES:
        _fail("manifest-shape", f"{label}.bytes is invalid")
    if not _valid_sha(value["sha256"]):
        _fail("manifest-shape", f"{label}.sha256 is invalid")


def _validate_pure_manifest_v1(value: Any) -> dict[str, Any]:
    """Validate the complete repository-independent freeze contract.

    This deliberately does not inspect the repository.  ``check_manifest``
    performs that separate identity/recomputation phase; custody can therefore
    authenticate exact canonical bytes and all frozen semantics without a
    rebuild or a repository substitution.
    """
    top_keys = {"schema", "manifest_sha256", "candidate_source_commit", "status", "lifecycle", "execution_permitted", "binding", "protocol", "raw_inputs", "repository_inputs", "candidate_closure", "runtime_tool_identities", "provenance_tool_identities", "build", "platform", "binaries", "readiness", "attempts", "canonicalization"}
    _pure_keys(value, top_keys, "manifest")
    if value["schema"] != V1_SCHEMA or value["status"] != "Proposed" or value["lifecycle"] != "planned" or value["execution_permitted"] is not False:
        _fail("manifest-shape", "manifest fixed state is not the freeze contract")
    if not _valid_commit(value["candidate_source_commit"]):
        _fail("manifest-shape", "candidate source commit is invalid")
    if value["manifest_sha256"] != _self_hash(value):
        _fail("manifest-self-hash", "manifest self hash does not match")
    _pure_keys(value["binding"], {"experiment_id", "phase_id", "candidate_profile_id"}, "manifest.binding")
    if value["binding"] != {"experiment_id": EXPERIMENT_ID, "phase_id": PHASE_ID, "candidate_profile_id": CANDIDATE_PROFILE_ID}:
        _fail("manifest-shape", "manifest binding values are wrong")
    protocol = {"request_protocol_id": REQUEST_PROTOCOL, "response_protocol_id": RESPONSE_PROTOCOL, "request_fields": REQUEST_FIELDS, "canonical_wire": "strict UTF-8 JSON object, exact seven request fields, canonical bytes are SHA-256 framed by the evidence contract"}
    if value["protocol"] != protocol:
        _fail("manifest-shape", "manifest protocol contract is wrong")
    canonicalization = {"encoding": "UTF-8", "json": "RFC 8259-compatible strict JSON", "sort_keys": True, "separators": [",", ":"], "ensure_ascii": True, "trailing_newline": True, "self_hash_domain": V1_HASH_DOMAIN.decode("ascii").rstrip("\0"), "self_hash_excludes": ["manifest_sha256"], "raw_file_hash": "SHA-256 over exact bytes; no parse/reserialize for raw identities"}
    if value["canonicalization"] != canonicalization:
        _fail("manifest-shape", "manifest canonicalization contract is wrong")
    if value["attempts"] != "per-attempt observations and Ben authorization are external to this manifest":
        _fail("manifest-shape", "manifest attempts contract is wrong")

    closure = value["candidate_closure"]
    _pure_keys(closure, {"count", "total_raw_bytes", "path_set_sha256", "content_sha256", "algorithm", "base_commit", "entries"}, "manifest.candidate_closure")
    if closure["algorithm"] != "ck.phase3-candidate-source-build-closure.v1" or not _valid_commit(closure["base_commit"]):
        _fail("manifest-shape", "candidate closure algorithm/base commit is wrong")
    if not isinstance(closure["entries"], list) or type(closure["count"]) is not int or closure["count"] <= 0 or closure["count"] != len(closure["entries"]):
        _fail("manifest-shape", "candidate closure count is wrong")
    if type(closure["total_raw_bytes"]) is not int or closure["total_raw_bytes"] < 0:
        _fail("manifest-shape", "candidate closure totals are wrong")
    path_stream = bytearray(b"ck.phase3-candidate-source-build-path-set.v1\0")
    total = 0
    previous: bytes | None = None
    for index, entry in enumerate(closure["entries"]):
        _pure_identity(entry, f"manifest.candidate_closure.entries[{index}]", full_mode=True)
        path = entry["path"].encode("utf-8")
        if previous is not None and path <= previous:
            _fail("manifest-shape", "candidate closure entries are not strictly ordered")
        previous = path
        mode = int(entry["mode"])
        size = int(entry["bytes"])
        path_stream += struct.pack(">I", len(path)) + path + struct.pack(">I", mode)
        total += size
    if total != closure["total_raw_bytes"] or not _valid_sha(closure["content_sha256"]) or _sha256(bytes(path_stream)) != closure["path_set_sha256"]:
        _fail("manifest-shape", "candidate closure digest fields do not match entries")

    for field, expected_paths in (("raw_inputs", list((*PACKAGE_INPUTS, FIXTURE_REL))), ("runtime_tool_identities", list(RUNTIME_TOOLS)), ("provenance_tool_identities", list(PROVENANCE_TOOLS))):
        collection = value[field]
        if not isinstance(collection, list) or [item.get("path") for item in collection if isinstance(item, Mapping)] != expected_paths:
            _fail("manifest-shape", f"manifest.{field} paths are not the closed contract")
        for index, identity in enumerate(collection):
            _pure_identity(identity, f"manifest.{field}[{index}]")

    repository_inputs = value["repository_inputs"]
    _pure_keys(repository_inputs, {"native_build_workflow"}, "manifest.repository_inputs")
    workflow = repository_inputs["native_build_workflow"]
    _pure_keys(workflow, {"path", "identity", "runner_label", "pinned_action_refs"}, "manifest.native_build_workflow")
    if workflow["path"] != WORKFLOW_REL or workflow["runner_label"] != "ubuntu-24.04" or not isinstance(workflow["pinned_action_refs"], list) or any(not isinstance(ref, str) or "@" not in ref or not ACTION_SHA_RE.fullmatch(ref.rsplit("@", 1)[1]) for ref in workflow["pinned_action_refs"]):
        _fail("manifest-shape", "native workflow contract is wrong")
    _pure_identity(workflow["identity"], "manifest.native_build_workflow.identity")
    if workflow["identity"]["path"] != WORKFLOW_REL:
        _fail("manifest-shape", "native workflow identity path is wrong")

    build = value["build"]
    _pure_keys(build, {"recipe", "toolchain", "dependencies"}, "manifest.build")
    if build["recipe"] != _build_recipe():
        _fail("manifest-shape", "build recipe differs from the frozen contract")
    toolchain = build["toolchain"]
    _pure_keys(toolchain, {"rust_toolchain_file", "rust_toolchain_file_identity", "channel", "profile", "components", "rustc", "cargo", "receipt_contract"}, "manifest.build.toolchain")
    if toolchain["rust_toolchain_file"] != "rust-toolchain.toml" or toolchain["channel"] != TOOLCHAIN or toolchain["profile"] != "minimal" or toolchain["components"] != ["rustfmt", "clippy"]:
        _fail("manifest-shape", "toolchain contract is wrong")
    _pure_identity(toolchain["rust_toolchain_file_identity"], "manifest.build.toolchain.rust_toolchain_file_identity")
    if toolchain["rustc"] != {"release": TOOLCHAIN, "commit_hash": "8bab26f4f68e0e26f0bb7960be334d5b520ea452", "host": TARGET, "llvm": "22.1.6"} or toolchain["cargo"] != {"release": TOOLCHAIN, "commit_hash": "c980f4866141969fab6254a680546a277789d6f0"}:
        _fail("manifest-shape", "toolchain identity contract is wrong")
    expected_receipt_contract = {"rust_toolchain": TOOLCHAIN, "rustc_prefix": "rustc 1.97.1", "rustc_commit_hash": "8bab26f4f68e0e26f0bb7960be334d5b520ea452", "rustc_host": TARGET, "rustc_llvm": "22.1.6", "cargo_prefix": "cargo 1.97.1", "cargo_commit_hash": "c980f4866141969fab6254a680546a277789d6f0", "cargo_host": TARGET, "python_prefix": "Python 3"}
    if toolchain["receipt_contract"] != expected_receipt_contract:
        _fail("manifest-shape", "toolchain receipt contract is wrong")
    dependencies = build["dependencies"]
    _pure_keys(dependencies, {"cargo_lock", "dependency_closure_contract", "vendor_closure_contract", "cargo_config_contract", "offline"}, "manifest.build.dependencies")
    _pure_identity(dependencies["cargo_lock"], "manifest.build.dependencies.cargo_lock")
    if dependencies["cargo_lock"]["path"] != CANDIDATE_LOCK_REL or dependencies["offline"] is not True:
        _fail("manifest-shape", "dependency lock/offline contract is wrong")
    if dependencies["dependency_closure_contract"] != {"schema": "ck.exp-0002.phase3.gate-b-cargo-metadata-1", "algorithm": "ck.exp-0002.phase3.gate-b-dependency-closure.v1", "fields": RECEIPT_DEPENDENCY_FIELDS} or dependencies["vendor_closure_contract"] != {"algorithm": "ck.exp-0002.phase3.gate-b-vendor-closure.v1", "fields": RECEIPT_VENDOR_FIELDS, "role_path_pattern": "phase3-gate-b-{platform_role}-vendor"} or dependencies["cargo_config_contract"] != {"algorithm": "ck.exp-0002.phase3.gate-b-controlled-vendor-config.v1", "fields": ["role_path", "algorithm", "sha256", "bytes"], "role_path_pattern": "phase3-gate-b-{platform_role}-cargo-config"}:
        _fail("manifest-shape", "dependency/vendor/config contract is wrong")
    if value["platform"] != _platforms():
        _fail("manifest-shape", "platform contract is wrong")
    binaries = _validate_binary_slots(value["binaries"])
    if any(slot["status"] == "bound" and slot["receipt_path"] != RECEIPT_PATHS[selector] for selector, slot in binaries.items()):
        _fail("manifest-shape", "binary receipt paths are wrong")
    if value["readiness"] != _readiness(binaries):
        _fail("manifest-shape", "manifest readiness contract is wrong")
    return dict(value)


def _v2_canonicalization() -> dict[str, Any]:
    return {
        "encoding": "UTF-8",
        "json": "RFC 8259-compatible strict JSON",
        "sort_keys": True,
        "separators": [",", ":"],
        "ensure_ascii": True,
        "trailing_newline": True,
        "self_hash_domain": HASH_DOMAIN.decode("ascii").rstrip("\0"),
        "self_hash_excludes": ["manifest_sha256"],
        "raw_file_hash": "SHA-256 over exact bytes; no parse/reserialize for raw identities",
    }


def _inherited_v1_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    """Return the complete closed set of facts v2 must inherit from exact v1."""
    try:
        return {field: json.loads(json.dumps(value[field])) for field in INHERITED_SUCCESSOR_FIELDS}
    except (KeyError, TypeError, ValueError, RecursionError) as error:
        raise FreezeManifestError("manifest-shape", "inherited v1 projection is incomplete") from error


def _inherited_v1_hash(value: Mapping[str, Any]) -> str:
    return _sha256(INHERITED_V1_HASH_DOMAIN + _canonical(_inherited_v1_projection(value)))


def _v1_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    """Project inherited v2 facts through the immutable v1 pure validator."""
    projected = json.loads(json.dumps(value))
    for field in (
        "predecessor_manifest_sha256", "predecessor_inherited_sha256", "execution_tool_source_commit",
        "exact_runtime_tool_identities", "predecessor_v1_manifest_sha256", "predecessor_v2_inherited_sha256",
        "previous_execution_tool_source_commit", "old_materialization_commit", "materialization_commit",
        "experiment_closure_tool_identities", "experiment_closure_schema",
        "predecessor_v2_manifest_sha256", "predecessor_v2_execution_tool_source_commit",
        "predecessor_v2_materialization_commit",
        "predecessor_v3_manifest_sha256", "predecessor_v3_execution_tool_source_commit",
        "predecessor_v3_materialization_commit", "predecessor_v4_manifest_sha256",
        "exact_python_runtime_contract",
        "predecessor_exact_python_runtime_contract",
    ):
        projected.pop(field, None)
    projected["schema"] = V1_SCHEMA
    if value.get("schema") == V5_SCHEMA:
        projected["provenance_tool_identities"] = projected["provenance_tool_identities"][:-1]
    projected["canonicalization"] = {
        **_v2_canonicalization(),
        "self_hash_domain": V1_HASH_DOMAIN.decode("ascii").rstrip("\0"),
    }
    projected["manifest_sha256"] = _self_hash(projected)
    return projected


def _validate_pure_manifest_v2(value: Any) -> dict[str, Any]:
    """Validate the successor freeze without consulting a repository."""
    top_keys = {
        "schema", "manifest_sha256", "predecessor_manifest_sha256",
        "predecessor_inherited_sha256",
        "candidate_source_commit", "execution_tool_source_commit", "status",
        "lifecycle", "execution_permitted", "binding", "protocol", "raw_inputs",
        "repository_inputs", "candidate_closure", "runtime_tool_identities",
        "exact_runtime_tool_identities", "provenance_tool_identities", "build",
        "platform", "binaries", "readiness", "attempts", "canonicalization",
    }
    _pure_keys(value, top_keys, "manifest")
    if value["schema"] != SCHEMA:
        _fail("manifest-shape", "manifest is not the current successor schema")
    if value["candidate_source_commit"] != EXPECTED_CANDIDATE_SOURCE_COMMIT:
        _fail("manifest-shape", "successor candidate source commit is not the frozen candidate")
    if not _valid_commit(value["execution_tool_source_commit"]) or value["execution_tool_source_commit"] == value["candidate_source_commit"]:
        _fail("manifest-shape", "execution tool source commit must be a distinct later full commit")
    if value["predecessor_manifest_sha256"] != EXPECTED_V1_MANIFEST_SHA256:
        _fail("manifest-shape", "predecessor manifest hash is not the exact historical v1 freeze")
    inherited_hash = _inherited_v1_hash(value)
    if value["predecessor_inherited_sha256"] != EXPECTED_INHERITED_V1_SHA256 or inherited_hash != EXPECTED_INHERITED_V1_SHA256:
        _fail("manifest-shape", "successor inherited facts differ from the exact historical v1 freeze")
    if value["canonicalization"] != _v2_canonicalization():
        _fail("manifest-shape", "manifest canonicalization contract is wrong")
    if value["manifest_sha256"] != _self_hash(value):
        _fail("manifest-self-hash", "manifest self hash does not match")

    collections = (
        ("runtime_tool_identities", RUNTIME_TOOLS),
        ("exact_runtime_tool_identities", LEGACY_EXACT_RUNTIME_TOOLS),
        ("provenance_tool_identities", PROVENANCE_TOOLS),
    )
    observed_paths: list[str] = []
    for field, expected_paths in collections:
        collection = value[field]
        if not isinstance(collection, list) or [item.get("path") for item in collection if isinstance(item, Mapping)] != list(expected_paths):
            _fail("manifest-shape", f"manifest.{field} paths are not the closed contract")
        for index, identity in enumerate(collection):
            _pure_identity(identity, f"manifest.{field}[{index}]")
        observed_paths.extend(expected_paths)
    if len(observed_paths) != 19 or len(set(observed_paths)) != 19:
        _fail("manifest-shape", "successor tool collections are not exactly 19 disjoint identities")

    # All other semantic sections remain byte-for-byte compatible with the v1
    # contract.  Reusing the frozen validator avoids a second subtly divergent
    # definition of the candidate/build/receipt/platform facts.
    _validate_pure_manifest_v1(_v1_projection(value))
    return dict(value)


def _v3_canonicalization() -> dict[str, Any]:
    return {
        "encoding": "UTF-8",
        "json": "RFC 8259-compatible strict JSON",
        "sort_keys": True,
        "separators": [",", ":"],
        "ensure_ascii": True,
        "trailing_newline": True,
        "self_hash_domain": V3_HASH_DOMAIN.decode("ascii").rstrip("\0"),
        "self_hash_excludes": ["manifest_sha256"],
        "raw_file_hash": "SHA-256 over exact bytes; no parse/reserialize for raw identities",
    }


def _validate_pure_manifest_v3(value: Any) -> dict[str, Any]:
    """Validate the immutable successor derived from exact v2 bytes.

    v3 keeps v1 and v2 identities as history, then binds the new closure
    adjudicator and all current execution/provenance tools to a later E/M
    chain.  Repository ancestry/current-disk checks remain in ``check_manifest``.
    """
    top_keys = {
        "schema", "manifest_sha256", "predecessor_manifest_sha256",
        "predecessor_inherited_sha256", "predecessor_v1_manifest_sha256", "predecessor_v2_inherited_sha256",
        "previous_execution_tool_source_commit", "old_materialization_commit",
        "materialization_commit", "candidate_source_commit", "execution_tool_source_commit",
        "status", "lifecycle", "execution_permitted", "binding", "protocol", "raw_inputs",
        "repository_inputs", "candidate_closure", "runtime_tool_identities",
        "exact_runtime_tool_identities", "provenance_tool_identities",
        "experiment_closure_tool_identities", "experiment_closure_schema", "build",
        "platform", "binaries", "readiness", "attempts", "canonicalization",
    }
    _pure_keys(value, top_keys, "manifest")
    if value["schema"] != V3_SCHEMA:
        _fail("manifest-shape", "manifest is not the v3 successor schema")
    if value["candidate_source_commit"] != EXPECTED_CANDIDATE_SOURCE_COMMIT:
        _fail("manifest-shape", "v3 candidate source commit is not the frozen candidate")
    for field in ("previous_execution_tool_source_commit", "old_materialization_commit", "materialization_commit", "execution_tool_source_commit"):
        if not _valid_commit(value[field]):
            _fail("manifest-shape", f"v3 {field} is not a full commit")
    if value["previous_execution_tool_source_commit"] != EXPECTED_V2_EXECUTION_TOOL_SOURCE_COMMIT:
        _fail("manifest-shape", "v3 previous execution commit is not the exact v2 E")
    if value["execution_tool_source_commit"] in {value["candidate_source_commit"], value["previous_execution_tool_source_commit"]}:
        _fail("manifest-shape", "v3 new execution commit must be distinct from C and old E")
    if value["old_materialization_commit"] == value["materialization_commit"]:
        _fail("manifest-shape", "v3 old and new materialization commits must be distinct")
    if value["predecessor_manifest_sha256"] != EXPECTED_V2_MANIFEST_SHA256 or value["predecessor_v1_manifest_sha256"] != EXPECTED_V1_MANIFEST_SHA256:
        _fail("manifest-shape", "v3 predecessor history does not retain exact v1/v2 hashes")
    if value["predecessor_inherited_sha256"] != EXPECTED_INHERITED_V1_SHA256 or value["predecessor_v2_inherited_sha256"] != EXPECTED_INHERITED_V1_SHA256:
        _fail("manifest-shape", "v3 predecessor history does not retain v2 inherited identity")
    if value["experiment_closure_schema"] != "ck.exp-0002.phase3.experiment-closure-1":
        _fail("manifest-shape", "v3 closure schema binding is wrong")
    if value["canonicalization"] != _v3_canonicalization():
        _fail("manifest-shape", "v3 canonicalization contract is wrong")
    if value["manifest_sha256"] != _self_hash(value):
        _fail("manifest-self-hash", "v3 manifest self hash does not match")
    for field, expected_paths in (
        ("runtime_tool_identities", RUNTIME_TOOLS),
        ("exact_runtime_tool_identities", LEGACY_EXACT_RUNTIME_TOOLS),
        ("provenance_tool_identities", PROVENANCE_TOOLS),
        ("experiment_closure_tool_identities", EXPERIMENT_CLOSURE_TOOLS),
    ):
        collection = value[field]
        if not isinstance(collection, list) or [item.get("path") for item in collection if isinstance(item, Mapping)] != list(expected_paths):
            _fail("manifest-shape", f"manifest.{field} paths are not the closed v3 contract")
        for index, identity in enumerate(collection):
            _pure_identity(identity, f"manifest.{field}[{index}]")
    # Reuse the v1 semantic validator for all C-bound facts.  This keeps v3
    # from silently resealing a changed corpus, binary, or platform contract.
    _validate_pure_manifest_v1(_v1_projection(value))
    return dict(value)


def _v4_canonicalization() -> dict[str, Any]:
    return {
        "encoding": "UTF-8",
        "json": "RFC 8259-compatible strict JSON",
        "sort_keys": True,
        "separators": [",", ":"],
        "ensure_ascii": True,
        "trailing_newline": True,
        "self_hash_domain": V4_HASH_DOMAIN.decode("ascii").rstrip("\0"),
        "self_hash_excludes": ["manifest_sha256"],
        "raw_file_hash": "SHA-256 over exact bytes; no parse/reserialize for raw identities",
    }


def _validate_pure_manifest_v4(value: Any) -> dict[str, Any]:
    """Validate the v3 successor that binds exact Python runtime facts."""
    top_keys = {
        "schema", "manifest_sha256", "predecessor_manifest_sha256",
        "predecessor_inherited_sha256", "predecessor_v1_manifest_sha256", "predecessor_v2_inherited_sha256",
        "predecessor_v2_manifest_sha256", "predecessor_v2_execution_tool_source_commit",
        "predecessor_v2_materialization_commit",
        "previous_execution_tool_source_commit", "old_materialization_commit",
        "materialization_commit", "candidate_source_commit", "execution_tool_source_commit",
        "status", "lifecycle", "execution_permitted", "binding", "protocol", "raw_inputs",
        "repository_inputs", "candidate_closure", "runtime_tool_identities",
        "exact_runtime_tool_identities", "provenance_tool_identities",
        "experiment_closure_tool_identities", "experiment_closure_schema", "build",
        "platform", "binaries", "readiness", "attempts", "canonicalization",
        "exact_python_runtime_contract",
    }
    _pure_keys(value, top_keys, "manifest")
    if value["schema"] != V4_SCHEMA:
        _fail("manifest-shape", "manifest is not the v4 successor schema")
    if value["candidate_source_commit"] != EXPECTED_CANDIDATE_SOURCE_COMMIT:
        _fail("manifest-shape", "v4 candidate source commit is not the frozen candidate")
    for field in ("previous_execution_tool_source_commit", "old_materialization_commit", "materialization_commit", "execution_tool_source_commit"):
        if not _valid_commit(value[field]):
            _fail("manifest-shape", f"v4 {field} is not a full commit")
    if value["execution_tool_source_commit"] in {value["candidate_source_commit"], value["previous_execution_tool_source_commit"]}:
        _fail("manifest-shape", "v4 new execution commit must be distinct from C and old E")
    if value["old_materialization_commit"] == value["materialization_commit"]:
        _fail("manifest-shape", "v4 old and new materialization commits must be distinct")
    if value["predecessor_manifest_sha256"] != EXPECTED_V3_MANIFEST_SHA256:
        _fail("manifest-shape", "v4 predecessor is not the exact v3 freeze")
    if value["predecessor_v1_manifest_sha256"] != EXPECTED_V1_MANIFEST_SHA256:
        _fail("manifest-shape", "v4 history does not retain the exact v1 hash")
    if value["predecessor_v2_manifest_sha256"] != EXPECTED_V2_MANIFEST_SHA256:
        _fail("manifest-shape", "v4 history does not retain the exact v2 manifest hash")
    if value["predecessor_inherited_sha256"] != EXPECTED_INHERITED_V1_SHA256 or value["predecessor_v2_inherited_sha256"] != EXPECTED_INHERITED_V1_SHA256:
        _fail("manifest-shape", "v4 history does not retain the exact v1/v2 inherited identity")
    if value["predecessor_v2_execution_tool_source_commit"] != EXPECTED_V2_EXECUTION_TOOL_SOURCE_COMMIT:
        _fail("manifest-shape", "v4 history does not retain the exact v2 execution snapshot")
    if value["predecessor_v2_materialization_commit"] != EXPECTED_V2_MATERIALIZATION_COMMIT:
        _fail("manifest-shape", "v4 history does not retain the exact v2 materialization snapshot")
    if value["previous_execution_tool_source_commit"] != EXPECTED_V3_EXECUTION_TOOL_SOURCE_COMMIT:
        _fail("manifest-shape", "v4 previous execution commit is not the exact v3 execution snapshot")
    if value["old_materialization_commit"] != EXPECTED_V3_MATERIALIZATION_COMMIT:
        _fail("manifest-shape", "v4 old materialization commit is not the exact v3 materialization snapshot")
    if value["experiment_closure_schema"] != "ck.exp-0002.phase3.experiment-closure-1":
        _fail("manifest-shape", "v4 closure schema binding is wrong")
    if value["canonicalization"] != _v4_canonicalization():
        _fail("manifest-shape", "v4 canonicalization contract is wrong")
    if value["manifest_sha256"] != _self_hash(value):
        _fail("manifest-self-hash", "v4 manifest self hash does not match")
    _validate_python_runtime_contract(value["exact_python_runtime_contract"])
    for field, expected_paths in (
        ("runtime_tool_identities", RUNTIME_TOOLS),
        ("exact_runtime_tool_identities", EXACT_RUNTIME_TOOLS),
        ("provenance_tool_identities", PROVENANCE_TOOLS),
        ("experiment_closure_tool_identities", EXPERIMENT_CLOSURE_TOOLS),
    ):
        collection = value[field]
        if not isinstance(collection, list) or [item.get("path") for item in collection if isinstance(item, Mapping)] != list(expected_paths):
            _fail("manifest-shape", f"manifest.{field} paths are not the closed v4 contract")
        for index, identity in enumerate(collection):
            _pure_identity(identity, f"manifest.{field}[{index}]")
    # Reuse the immutable v1 semantic validator for all C-bound facts.  The
    # v3 validator cannot be reused directly because its E/M fields necessarily
    # advance in this successor.  The explicit lineage checks above retain the
    # v1/v2/v3 history while this projection prevents resealing changed inputs.
    _validate_pure_manifest_v1(_v1_projection(value))
    return dict(value)


def _v5_canonicalization() -> dict[str, Any]:
    return {
        "encoding": "UTF-8", "json": "RFC 8259-compatible strict JSON", "sort_keys": True,
        "separators": [",", ":"], "ensure_ascii": True, "trailing_newline": True,
        "self_hash_domain": V5_HASH_DOMAIN.decode("ascii").rstrip("\0"),
        "self_hash_excludes": ["manifest_sha256"],
        "raw_file_hash": "SHA-256 over exact bytes; no parse/reserialize for raw identities",
    }


def _validate_pure_manifest_v5(value: Any) -> dict[str, Any]:
    """Validate the content-addressed runtime successor without repository IO."""
    top_keys = {
        "schema", "manifest_sha256", "predecessor_manifest_sha256", "predecessor_inherited_sha256",
        "predecessor_v1_manifest_sha256", "predecessor_v2_inherited_sha256", "predecessor_v2_manifest_sha256",
        "predecessor_v2_execution_tool_source_commit", "predecessor_v2_materialization_commit",
        "predecessor_v3_manifest_sha256", "predecessor_v3_execution_tool_source_commit", "predecessor_v3_materialization_commit",
        "predecessor_v4_manifest_sha256", "predecessor_exact_python_runtime_contract",
        "previous_execution_tool_source_commit", "old_materialization_commit", "materialization_commit",
        "candidate_source_commit", "execution_tool_source_commit", "status", "lifecycle", "execution_permitted",
        "binding", "protocol", "raw_inputs", "repository_inputs", "candidate_closure", "runtime_tool_identities",
        "exact_runtime_tool_identities", "provenance_tool_identities", "experiment_closure_tool_identities",
        "experiment_closure_schema", "build", "platform", "binaries", "readiness", "attempts", "canonicalization",
        "exact_python_runtime_contract",
    }
    _pure_keys(value, top_keys, "manifest")
    if value["schema"] != V5_SCHEMA or value["candidate_source_commit"] != EXPECTED_CANDIDATE_SOURCE_COMMIT:
        _fail("manifest-shape", "manifest is not the v5 successor for the fixed candidate")
    if value["predecessor_manifest_sha256"] != EXPECTED_V4_MANIFEST_SHA256 or value["predecessor_v4_manifest_sha256"] != EXPECTED_V4_MANIFEST_SHA256:
        _fail("manifest-shape", "v5 predecessor is not the exact immutable v4 freeze")
    if value["predecessor_v1_manifest_sha256"] != EXPECTED_V1_MANIFEST_SHA256 or value["predecessor_v2_manifest_sha256"] != EXPECTED_V2_MANIFEST_SHA256 or value["predecessor_v3_manifest_sha256"] != EXPECTED_V3_MANIFEST_SHA256:
        _fail("manifest-shape", "v5 history does not retain exact predecessor hashes")
    if value["predecessor_inherited_sha256"] != EXPECTED_INHERITED_V1_SHA256 or value["predecessor_v2_inherited_sha256"] != EXPECTED_INHERITED_V1_SHA256:
        _fail("manifest-shape", "v5 history does not retain exact inherited identity")
    for field in ("predecessor_v3_execution_tool_source_commit", "predecessor_v3_materialization_commit", "previous_execution_tool_source_commit", "old_materialization_commit", "materialization_commit", "execution_tool_source_commit"):
        if not _valid_commit(value[field]):
            _fail("manifest-shape", f"v5 {field} is not a full commit")
    if value["predecessor_v3_execution_tool_source_commit"] != EXPECTED_V3_EXECUTION_TOOL_SOURCE_COMMIT or value["predecessor_v3_materialization_commit"] != EXPECTED_V3_MATERIALIZATION_COMMIT:
        _fail("manifest-shape", "v5 history does not retain exact v3 execution/materialization snapshots")
    if value["previous_execution_tool_source_commit"] != EXPECTED_V4_EXECUTION_TOOL_SOURCE_COMMIT or value["old_materialization_commit"] != EXPECTED_V4_MATERIALIZATION_COMMIT:
        _fail("manifest-shape", "v5 old execution/materialization snapshots are not the exact v4 snapshots")
    if value["previous_execution_tool_source_commit"] == value["candidate_source_commit"] or value["execution_tool_source_commit"] in {value["candidate_source_commit"], value["previous_execution_tool_source_commit"]}:
        _fail("manifest-shape", "v5 execution snapshots are not distinct")
    if value["old_materialization_commit"] == value["materialization_commit"]:
        _fail("manifest-shape", "v5 materialization snapshots are not distinct")
    if value["experiment_closure_schema"] != "ck.exp-0002.phase3.experiment-closure-1" or value["canonicalization"] != _v5_canonicalization():
        _fail("manifest-shape", "v5 closure/canonicalization contract is wrong")
    if value["manifest_sha256"] != _self_hash(value):
        _fail("manifest-self-hash", "v5 manifest self hash does not match")
    _validate_python_runtime_contract(value["predecessor_exact_python_runtime_contract"])
    _validate_python_runtime_contract_v2(value["exact_python_runtime_contract"])
    for field, expected_paths in (
        ("runtime_tool_identities", RUNTIME_TOOLS),
        ("exact_runtime_tool_identities", EXACT_RUNTIME_TOOLS),
        ("provenance_tool_identities", V5_PROVENANCE_TOOLS),
        ("experiment_closure_tool_identities", EXPERIMENT_CLOSURE_TOOLS),
    ):
        collection = value[field]
        if not isinstance(collection, list) or [item.get("path") for item in collection if isinstance(item, Mapping)] != list(expected_paths):
            _fail("manifest-shape", f"manifest.{field} paths are not the closed v5 contract")
        for index, identity in enumerate(collection):
            _pure_identity(identity, f"manifest.{field}[{index}]")
    _validate_pure_manifest_v1(_v1_projection(value))
    return dict(value)


def _seal(value: dict[str, Any]) -> dict[str, Any]:
    value["manifest_sha256"] = _self_hash(value)
    return value


def _validate_binary_slots(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != set(SELECTORS):
        _fail("binary-binding", "binary slots are incomplete or unexpected")
    return _binary_slots(value)


def _package_extra_files(package: Path, *, allow_v5_runtime_attestations: bool = False) -> list[str]:
    """Return package files outside the closed freeze input policy.

    Runtime-attestation sidecars are reserved for a v5 package.  Even there,
    only the two selector-specific canonical paths are permitted; all other
    files remain extras.
    """
    found: list[str] = []
    allowed_attestations = set(RUNTIME_ATTESTATION_PATHS.values()) if allow_v5_runtime_attestations else set()
    for directory in ("corpora", "manifests"):
        base = _safe_path(package, directory)
        if not base.is_dir():
            _fail("missing-directory", directory)
        for path in base.rglob("*"):
            relative = path.relative_to(package).as_posix()
            if relative.startswith(RECEIPT_DIR_REL + "/"):
                if path.is_symlink() or not path.is_file() or relative not in set(RECEIPT_PATHS.values()):
                    found.append(relative)
            elif relative.startswith("manifests/runtime-attestations/"):
                if path.is_symlink() or not path.is_file() or relative not in allowed_attestations:
                    found.append(relative)
            elif path.is_symlink():
                found.append(relative)
            elif path.is_file() and relative not in RELEVANT_PACKAGE_FILES:
                found.append(relative)
    return sorted(found)


def generate_manifest(
    repo: Path = REPO,
    package: Path = PACKAGE,
    *,
    binaries: Mapping[str, Any] | None = None,
    source_commit: str | None = None,
    allow_v5_runtime_attestations: bool = False,
) -> dict[str, Any]:
    """Generate the historical v1 shape; successor generation is explicit."""
    extras = _package_extra_files(package, allow_v5_runtime_attestations=allow_v5_runtime_attestations)
    if extras:
        _fail("extra-input", ", ".join(extras))
    resolved_commit = _resolve_source_commit(repo, source_commit)
    return _seal(_base_manifest(repo, package, binaries=binaries, source_commit=resolved_commit))


def validate_manifest(raw_or_value: bytes | Mapping[str, Any]) -> dict[str, Any]:
    """Validate exact canonical bytes and the complete pure freeze contract."""
    if isinstance(raw_or_value, bytes):
        raw = raw_or_value
        if len(raw) > MAX_MANIFEST_BYTES or not raw.endswith(b"\n"):
            _fail("manifest-read", "manifest bytes are absent, oversized, or missing the trailing newline")
        try:
            def collect(items: list[tuple[str, Any]]) -> dict[str, Any]:
                keys = [key for key, _ in items]
                if len(keys) != len(set(keys)):
                    _fail("manifest-shape", "manifest contains duplicate JSON keys")
                return dict(items)
            value = json.loads(raw.decode("utf-8"), object_pairs_hook=collect, parse_constant=lambda token: _fail("manifest-shape", f"non-finite JSON value {token}"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise FreezeManifestError("manifest-read", "manifest is not strict JSON") from error
        if not isinstance(value, dict) or _canonical(value) != raw:
            _fail("manifest-canonical", "manifest bytes are not canonical")
    elif isinstance(raw_or_value, Mapping):
        value = dict(raw_or_value)
    else:
        _fail("manifest-shape", "manifest must be canonical bytes or a parsed object")
    schema = value.get("schema") if isinstance(value, Mapping) else None
    if schema == V1_SCHEMA:
        return _validate_pure_manifest_v1(value)
    if schema == SCHEMA:
        return _validate_pure_manifest_v2(value)
    if schema == V3_SCHEMA:
        return _validate_pure_manifest_v3(value)
    if schema == V4_SCHEMA:
        return _validate_pure_manifest_v4(value)
    if schema == V5_SCHEMA:
        return _validate_pure_manifest_v5(value)
    _fail("manifest-shape", "manifest schema is unsupported")


def _load_manifest(path: Path, *, raw: bytes | None = None) -> dict[str, Any]:
    if raw is None:
        raw = _read_manifest_bytes(path)
    try:
        return validate_manifest(raw)
    except FreezeManifestError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, RecursionError) as error:
        raise FreezeManifestError("manifest-read", str(path)) from error


def _manifest_identity(info: os.stat_result) -> tuple[int, int, int, int, int, int, int]:
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _read_manifest_snapshot(path: Path) -> tuple[bytes, tuple[int, int, int, int, int, int, int]]:
    """Read canonical bytes and the exact stable destination identity.

    The manifest is a publication boundary, so a path read is not sufficient:
    reject symlinks, non-regular files, hardlinks, and non-canonical modes and
    compare the descriptor identity before/after the bounded read.
    """
    for component in reversed(path.parents):
        try:
            if component.is_symlink():
                _fail("manifest-file", "manifest path contains a symlink component")
        except OSError as error:
            raise FreezeManifestError("manifest-file", str(path)) from error
    try:
        before = path.lstat()
    except OSError as error:
        raise FreezeManifestError("manifest-read", str(path)) from error
    if not stat.S_ISREG(before.st_mode) or stat.S_ISLNK(before.st_mode) or stat.S_IMODE(before.st_mode) != 0o644 or before.st_nlink != 1:
        _fail("manifest-file", "manifest must be a mode-0644 single-link regular file")
    if before.st_size > MAX_MANIFEST_BYTES:
        _fail("manifest-size", "manifest exceeds the bounded size")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        if getattr(error, "errno", None) == getattr(os, "ELOOP", 40):
            raise FreezeManifestError("manifest-file", "manifest is a symlink") from error
        raise FreezeManifestError("manifest-read", str(path)) from error
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or stat.S_ISLNK(opened.st_mode) or stat.S_IMODE(opened.st_mode) != 0o644 or opened.st_nlink != 1 or _manifest_identity(opened) != _manifest_identity(before):
            _fail("manifest-file", "manifest changed before reading")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(1024 * 1024, MAX_MANIFEST_BYTES + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > MAX_MANIFEST_BYTES:
                _fail("manifest-size", "manifest grew beyond the bounded size")
        raw = b"".join(chunks)
        after = os.fstat(descriptor)
    except FreezeManifestError:
        raise
    except OSError as error:
        raise FreezeManifestError("manifest-read", str(path)) from error
    finally:
        os.close(descriptor)
    if _manifest_identity(after) != (before.st_dev, before.st_ino, before.st_mode, before.st_nlink, len(raw), before.st_mtime_ns, before.st_ctime_ns):
        _fail("manifest-file", "manifest changed while reading")
    try:
        current = path.lstat()
    except OSError as error:
        raise FreezeManifestError("manifest-file", "manifest disappeared after reading") from error
    if _manifest_identity(current) != (before.st_dev, before.st_ino, before.st_mode, before.st_nlink, len(raw), before.st_mtime_ns, before.st_ctime_ns):
        _fail("manifest-file", "manifest changed after reading")
    return raw, _manifest_identity(current)


def _read_manifest_bytes(path: Path) -> bytes:
    return _read_manifest_snapshot(path)[0]


def _read_authenticated_file(path: Path, label: str, expected: Mapping[str, Any] | None, *, maximum: int = MAX_FILE_BYTES) -> bytes:
    """Read a frozen tool/receipt through anchored, stable descriptors."""
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
        identity = lambda info: (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
        if stat.S_ISLNK(before_path.st_mode) or not stat.S_ISREG(before_path.st_mode) or stat.S_IMODE(before_path.st_mode) != 0o644 or before_path.st_nlink != 1:
            _fail("frozen-file", f"{label} is not a mode-0644 single-link file")
        if before_path.st_size <= 0 or before_path.st_size > maximum:
            _fail("frozen-file", f"{label} is outside its bounded size")
        if expected is not None and (expected.get("mode") != 0o644 or expected.get("bytes") != before_path.st_size):
            _fail("frozen-file", f"{label} differs from its frozen size or mode")
        descriptor = os.open(name, flags, dir_fd=parent)
        opened = os.fstat(descriptor)
        if identity(opened) != identity(before_path):
            _fail("frozen-file", f"{label} changed before reading")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(1024 * 1024, maximum + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > maximum:
                _fail("frozen-file", f"{label} grew beyond its bound")
        raw = b"".join(chunks)
        after = os.fstat(descriptor)
        after_path = os.stat(name, dir_fd=parent, follow_symlinks=False)
        if identity(after) != identity(before_path) or identity(after_path) != identity(after) or len(raw) != before_path.st_size:
            _fail("frozen-file", f"{label} changed while reading")
        if expected is not None and (len(raw) != expected.get("bytes") or hashlib.sha256(raw).hexdigest() != expected.get("sha256")):
            _fail("frozen-file", f"{label} differs from its frozen identity")
        return raw
    except FreezeManifestError:
        raise
    except OSError as error:
        raise FreezeManifestError("frozen-file", f"cannot read {label}") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if parent >= 0:
            os.close(parent)


def _tool_identity(manifest: Mapping[str, Any], path: str) -> dict[str, Any] | None:
    for field in ("runtime_tool_identities", "exact_runtime_tool_identities", "provenance_tool_identities"):
        identities = manifest.get(field)
        if isinstance(identities, list):
            for identity in identities:
                if isinstance(identity, Mapping) and identity.get("path") == path:
                    return dict(identity)
    return None


def _historical_receipt_source(relative: str, expected: Mapping[str, Any], manifest: Mapping[str, Any]) -> bytes | None:
    """Recover an authenticated predecessor receipt validator from Git.

    Historical v1-v4 manifests bind the receipt validator's exact source
    bytes.  When the current working copy has advanced that tool, retain the
    historical check by looking up the exact authenticated SHA-256 in the
    repository's reachable Git blobs.  Current v5 validation never falls back
    to history: its validator must be the freshly authenticated package file.
    """
    if manifest.get("schema") not in {V1_SCHEMA, V2_SCHEMA, V3_SCHEMA, V4_SCHEMA}:
        return None
    if expected.get("mode") != 0o644 or not isinstance(expected.get("bytes"), int) or not _valid_sha(expected.get("sha256")):
        return None
    repository_path = f"{PACKAGE_REL}/{relative}"
    try:
        listing = _git_run(
            REPO, "rev-list", "--objects", "--all", "--", repository_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError:
        return None
    if listing.returncode:
        return None
    for record in listing.stdout.splitlines():
        try:
            object_id, path_bytes = record.split(b" ", 1)
            path = path_bytes.decode("utf-8")
            object_text = object_id.decode("ascii")
        except (UnicodeDecodeError, ValueError):
            continue
        if path != repository_path or not _valid_commit(object_text):
            continue
        try:
            blob = _git_run(
                REPO, "cat-file", "blob", object_text,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except OSError:
            continue
        if blob.returncode or len(blob.stdout) > MAX_FILE_BYTES:
            continue
        if len(blob.stdout) == expected["bytes"] and _sha256(blob.stdout) == expected["sha256"]:
            return blob.stdout
    return None


def _receipt_module(package: Path, manifest: Mapping[str, Any]) -> Any:
    relative = "scripts/phase3_build_receipt.py"
    expected = _tool_identity(manifest, relative)
    if expected is None:
        _fail("build-receipt", "freeze does not authenticate the receipt validator")
    path = package / relative
    try:
        source = _read_authenticated_file(path, relative, expected)
    except FreezeManifestError as original_error:
        # Only a regular current file may use the exact historical Git-blob
        # fallback.  Missing, symlinked, or otherwise unsafe package inputs
        # remain fail-closed.
        if not original_error.detail.startswith(f"{relative} differs from its frozen"):
            raise
        try:
            info = path.lstat()
        except OSError:
            raise original_error
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o644 or info.st_nlink != 1:
            raise original_error
        source = _historical_receipt_source(relative, expected, manifest)
        if source is None:
            raise original_error
    module_name = f"phase3_build_receipt_for_freeze_{id(package)}"
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
        # Bind the freshly loaded receipt validator before its first caller
        # can validate a receipt (which may perform Git reads indirectly).
        module.GIT_EXECUTABLE = GIT_EXECUTABLE
        module.GIT_ENV = dict(GIT_ENV)
        return module
    except FreezeManifestError:
        raise
    except Exception as error:
        raise FreezeManifestError("build-receipt", "receipt validator cannot be loaded") from error


def _receipt_path(package: Path, path: Path) -> str:
    try:
        absolute = path.absolute()
        relative = absolute.relative_to(package.absolute()).as_posix()
    except ValueError as error:
        raise FreezeManifestError("build-receipt-path", "receipt must be under the package") from error
    if relative not in set(RECEIPT_PATHS.values()):
        _fail("build-receipt-path", "receipt must use the fixed WSL or native receipt path")
    _safe_path(package, relative)
    info = Path(absolute).lstat()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        _fail("build-receipt-path", "receipt must be a single-link regular non-symlink file")
    return relative


def _receipt_contract(manifest: Mapping[str, Any]) -> tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]]:
    try:
        artifact = manifest["build"]["recipe"]["artifact_build"]
        environment = artifact["environment"]
        dependencies = manifest["build"]["dependencies"]
        toolchain = manifest["build"]["toolchain"]
    except (KeyError, TypeError) as error:
        raise FreezeManifestError("build-recipe", "manifest receipt contract is incomplete") from error
    if artifact["argv_template"][:7] != ["cargo", "+1.97.1", "build", "--manifest-path", CANDIDATE_MANIFEST_REL, "--target", TARGET] or artifact["argv_template"][7:] != ["--target-dir", "<fresh-target-dir>", "--locked", "--offline"]:
        _fail("build-recipe", "artifact build argv template is not exact")
    if artifact["working_directory"] != "." or artifact["target"] != TARGET or artifact["profile"] != "dev" or environment != ENV_POLICY:
        _fail("build-recipe", "artifact build contract differs from receipt policy")
    return artifact, environment, dependencies, toolchain


def _load_build_receipt(path: Path, package: Path, expected_closure: Mapping[str, Any], manifest: Mapping[str, Any]) -> tuple[str, dict[str, Any], str, Mapping[str, Any]]:
    relative = _receipt_path(package, path)
    try:
        expected = None
        binaries = manifest.get("binaries") if isinstance(manifest, Mapping) else None
        if isinstance(binaries, Mapping):
            for slot in binaries.values():
                if isinstance(slot, Mapping) and slot.get("receipt_path") == relative:
                    expected = {"mode": 0o644, "bytes": slot.get("receipt_bytes"), "sha256": slot.get("receipt_sha256")}
                    break
        raw = _read_authenticated_file(path, relative, expected, maximum=MAX_RECEIPT_BYTES)
        module = _receipt_module(package, manifest)
        value = module.validate_receipt(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as error:
        raise FreezeManifestError("build-receipt", str(path)) from error
    if not isinstance(value, Mapping) or value.get("phase_id") != PHASE_ID or value.get("source_closure") is None:
        _fail("build-receipt", "receipt has the wrong fixed identity")
    closure = value["source_closure"]
    expected_source = {"algorithm": expected_closure["algorithm"], "base_commit": expected_closure["base_commit"], "files": expected_closure["count"], "bytes": expected_closure["total_raw_bytes"], "path_sha256": expected_closure["path_set_sha256"], "content_sha256": expected_closure["content_sha256"]}
    if dict(closure) != expected_source:
        _fail("build-receipt", "receipt source closure differs from frozen closure")
    build = value["build"]
    artifact, environment, dependencies, toolchain = _receipt_contract(manifest)
    selector = {"wsl": "wsl2-x86_64", "native": "ubuntu-24.04-x86_64"}.get(build.get("platform_role"))
    if selector not in SELECTORS or build.get("target") != TARGET or build.get("profile") != "dev" or build.get("cwd") != ".":
        _fail("build-receipt", "receipt platform/target/profile/cwd differs from freeze")
    if relative != RECEIPT_PATHS[selector]:
        _fail("build-receipt-path", "receipt path does not match its platform role")
    expected_prefix = artifact["argv_template"][:7]
    argv = build.get("argv")
    target_dir = argv[8] if isinstance(argv, list) and len(argv) == 11 and len(argv) > 8 else None
    if not isinstance(argv, list) or len(argv) != 11 or argv[:7] != expected_prefix or argv[7:] != ["--target-dir", target_dir, "--locked", "--offline"] or not isinstance(target_dir, str) or not os.path.isabs(target_dir):
        _fail("build-receipt", "receipt argv is not the exact sanitized artifact build")
    if build.get("env_policy") != environment:
        _fail("build-receipt", "receipt environment policy differs from frozen policy")
    receipt_toolchain = build.get("toolchain")
    contract = toolchain["receipt_contract"]
    rustc_facts = str(receipt_toolchain.get("rustc", "")) if isinstance(receipt_toolchain, Mapping) else ""
    cargo_facts = str(receipt_toolchain.get("cargo", "")) if isinstance(receipt_toolchain, Mapping) else ""
    rustc_required = (contract["rustc_prefix"], f"commit-hash: {contract['rustc_commit_hash']}", f"host: {contract['rustc_host']}", f"LLVM version: {contract['rustc_llvm']}")
    cargo_required = (contract["cargo_prefix"], f"commit-hash: {contract['cargo_commit_hash']}", f"host: {contract['cargo_host']}")
    if not isinstance(receipt_toolchain, Mapping) or receipt_toolchain.get("rust_toolchain") != contract["rust_toolchain"] or any(item not in rustc_facts for item in rustc_required) or any(item not in cargo_facts for item in cargo_required) or not str(receipt_toolchain.get("python", "")).startswith(contract["python_prefix"]):
        _fail("build-receipt", "receipt toolchain facts differ from frozen toolchain contract")
    lock = build.get("cargo_lock")
    frozen_lock = dependencies["cargo_lock"]
    if not isinstance(lock, Mapping) or {key: lock.get(key) for key in ("path", "sha256", "bytes")} != {key: frozen_lock.get(key) for key in ("path", "sha256", "bytes")}:
        _fail("build-receipt", "receipt Cargo.lock identity differs from frozen lock")
    dep = build.get("dependency_closure")
    dep_contract = dependencies["dependency_closure_contract"]
    if not isinstance(dep, Mapping) or set(dep) != set(RECEIPT_DEPENDENCY_FIELDS) or dep.get("schema") != dep_contract["schema"] or dep.get("algorithm") != dep_contract["algorithm"]:
        _fail("build-receipt", "receipt dependency closure schema differs from frozen contract")
    vendor = build.get("vendor_closure")
    vendor_contract = dependencies["vendor_closure_contract"]
    expected_vendor_role = vendor_contract["role_path_pattern"].format(platform_role=build["platform_role"])
    if not isinstance(vendor, Mapping) or set(vendor) != set(RECEIPT_VENDOR_FIELDS) or vendor.get("algorithm") != vendor_contract["algorithm"] or vendor.get("role_path") != expected_vendor_role:
        _fail("build-receipt", "receipt vendor closure differs from frozen contract")
    observation = build.get("platform_observation")
    string_observation_fields = set(PLATFORM_OBSERVATION_FIELDS) - {"sanitized_environment_keys"}
    if not isinstance(observation, Mapping) or set(observation) != set(PLATFORM_OBSERVATION_FIELDS) or observation.get("stability") != "observed-for-this-build-only" or any(not isinstance(observation[key], str) or not observation[key] for key in string_observation_fields) or observation.get("sanitized_environment_keys") != sorted(ENV_POLICY["variables"]):
        _fail("build-receipt", "receipt platform observation differs from frozen contract")
    config = build.get("cargo_config")
    config_contract = dependencies["cargo_config_contract"]
    expected_config_role = config_contract["role_path_pattern"].format(platform_role=build["platform_role"])
    if not isinstance(config, Mapping) or set(config) != set(config_contract["fields"]) or config.get("role_path") != expected_config_role or config.get("algorithm") != config_contract["algorithm"] or not _valid_sha(config.get("sha256")) or type(config.get("bytes")) is not int or config["bytes"] <= 0:
        _fail("build-receipt", "receipt Cargo vendor config differs from frozen contract")
    binary = value.get("binary")
    expected_binary_role = artifact["binary_role_path_pattern"].format(platform_role=build["platform_role"], target=TARGET)
    expected_binary = artifact["binary_role_path_pattern"].format(platform_role=build["platform_role"], target=TARGET)
    if build.get("binary_role_path") != expected_binary_role or not isinstance(binary, Mapping) or binary.get("role") != "phase3-candidate" or binary.get("path") != expected_binary:
        _fail("build-receipt", "receipt binary role path differs from frozen contract")
    if not _valid_sha(binary.get("sha256")) or type(binary.get("bytes")) is not int or binary["bytes"] <= 0:
        _fail("build-receipt", "receipt binary identity is invalid")
    mode = binary.get("mode")
    try:
        full_mode = stat.S_IFREG | int(mode, 8)
    except (TypeError, ValueError):
        _fail("build-receipt", "receipt binary mode is invalid")
    if not stat.S_ISREG(full_mode):
        _fail("build-receipt", "receipt binary mode is not regular")
    binding = {
        "status": "bound", "receipt_path": relative, "receipt_bytes": len(raw), "receipt_sha256": _sha256(raw),
        "receipt_self_hash": value["receipt_sha256"], "binary_identity": {"bytes": binary["bytes"], "mode": full_mode, "sha256": binary["sha256"]},
    }
    return selector, binding, value["source_commit"], value


def _dependency_logical(value: Mapping[str, Any]) -> dict[str, Any]:
    """Return dependency facts stable across platform metadata captures."""
    return {key: value[key] for key in ("schema", "algorithm", "sha256", "packages", "nodes")}


def _vendor_logical(value: Mapping[str, Any]) -> dict[str, Any]:
    """Return vendor facts while excluding the platform-specific role path."""
    return {key: value[key] for key in ("algorithm", "files", "bytes", "path_sha256", "content_sha256")}


def _validate_bound_receipts(package: Path, manifest: Mapping[str, Any], binaries: Mapping[str, Any]) -> None:
    paths = []
    for selector in SELECTORS:
        slot = binaries[selector]
        if slot["status"] == "bound":
            paths.append((selector, package / slot["receipt_path"]))
    if not paths:
        return
    commits: set[str] = set()
    build_facts: list[Mapping[str, Any]] = []
    for selector, path in paths:
        actual_selector, binding, commit, value = _load_build_receipt(path, package, manifest["candidate_closure"], manifest)
        if actual_selector != selector or binding != binaries[selector]:
            _fail("receipt-drift", f"receipt binding for {selector} differs from manifest")
        if commit != manifest.get("candidate_source_commit"):
            _fail("source-commit", f"receipt source commit for {selector} differs from manifest")
        commits.add(commit)
        build_facts.append(value["build"])
    if len(paths) == 2 and len(commits) != 1:
        _fail("build-receipt", "WSL and native receipts do not use the same full source commit")
    if len(build_facts) == 2 and (_dependency_logical(build_facts[0]["dependency_closure"]) != _dependency_logical(build_facts[1]["dependency_closure"]) or _vendor_logical(build_facts[0]["vendor_closure"]) != _vendor_logical(build_facts[1]["vendor_closure"])):
        _fail("build-receipt", "platform receipts do not share the same dependency/vendor closure")


def _validate_current_candidate_build_inputs(repo: Path, package: Path, manifest: Mapping[str, Any]) -> None:
    """Recompute inherited v1 facts while deliberately ignoring changed tools."""
    current = generate_manifest(
        repo,
        package,
        binaries=_validate_binary_slots(manifest.get("binaries")),
        source_commit=manifest.get("candidate_source_commit"),
        allow_v5_runtime_attestations=manifest.get("schema") == V5_SCHEMA,
    )
    for field in INHERITED_SUCCESSOR_FIELDS:
        if manifest.get(field) != current.get(field):
            _fail("manifest-drift", f"successor inherited field differs from current inputs: {field}")


def build_successor_manifest(
    predecessor_raw: bytes,
    *,
    execution_tool_source_commit: str,
    repo: Path = REPO,
    package: Path = PACKAGE,
) -> dict[str, Any]:
    """Build v2 from exact canonical, fully bound v1 bytes without executing."""
    if not isinstance(predecessor_raw, bytes):
        _fail("predecessor-manifest", "successor input must be the exact v1 bytes")
    predecessor = validate_manifest(predecessor_raw)
    if predecessor.get("schema") != V1_SCHEMA:
        _fail("predecessor-manifest", "successor input must be the historical v1 manifest")
    if predecessor.get("manifest_sha256") != EXPECTED_V1_MANIFEST_SHA256:
        _fail("predecessor-manifest", "successor input is not the exact canonical historical v1 manifest")
    binaries = _validate_binary_slots(predecessor.get("binaries"))
    if any(slot["status"] != "bound" for slot in binaries.values()):
        _fail("predecessor-manifest", "successor requires the fully bound historical v1 manifest")
    if predecessor.get("readiness") != _readiness(binaries) or predecessor["readiness"]["materialization_state"] != "frozen":
        _fail("predecessor-manifest", "historical v1 manifest is not frozen")
    if predecessor.get("candidate_source_commit") != EXPECTED_CANDIDATE_SOURCE_COMMIT:
        _fail("predecessor-manifest", "historical v1 manifest has the wrong candidate commit")
    if not _valid_commit(execution_tool_source_commit) or execution_tool_source_commit == predecessor["candidate_source_commit"]:
        _fail("execution-tool-commit", "caller must supply a distinct later full execution tool commit")

    # The predecessor is authenticated independently before any successor
    # fields are introduced. Its receipts and candidate-era closure remain
    # governed by C; only execution/provenance tools move to E.
    _validate_candidate_commit_snapshot(repo, package, predecessor)
    _validate_bound_receipts(package, predecessor, binaries)
    successor = json.loads(json.dumps(predecessor))
    successor["schema"] = SCHEMA
    successor["manifest_sha256"] = None
    successor["predecessor_manifest_sha256"] = predecessor["manifest_sha256"]
    successor["predecessor_inherited_sha256"] = _inherited_v1_hash(predecessor)
    successor["execution_tool_source_commit"] = execution_tool_source_commit
    successor["runtime_tool_identities"] = _execution_tool_identities_from_commit(repo, execution_tool_source_commit, RUNTIME_TOOLS)
    successor["exact_runtime_tool_identities"] = _execution_tool_identities_from_commit(repo, execution_tool_source_commit, LEGACY_EXACT_RUNTIME_TOOLS)
    successor["provenance_tool_identities"] = _execution_tool_identities_from_commit(repo, execution_tool_source_commit, PROVENANCE_TOOLS)
    successor["canonicalization"] = _v2_canonicalization()
    _seal(successor)
    validated = _validate_pure_manifest_v2(successor)
    _validate_candidate_build_snapshot(repo, validated)
    _validate_execution_commit_snapshot(repo, package, validated)
    return validated


def build_v3_successor_manifest(
    predecessor_raw: bytes,
    *,
    execution_tool_source_commit: str,
    old_materialization_commit: str = EXPECTED_V2_MATERIALIZATION_COMMIT,
    materialization_commit: str | None = None,
    new_materialization_commit: str | None = None,
    previous_execution_tool_source_commit: str = EXPECTED_V2_EXECUTION_TOOL_SOURCE_COMMIT,
    repo: Path = REPO,
    package: Path = PACKAGE,
) -> dict[str, Any]:
    """Build v3 from the exact current v2 bytes without execution.

    ``materialization_commit`` is intentionally explicit: it identifies the
    new package materialization snapshot (an ancestor of the later manifest
    publication commit).  Before the new E/M commits exist, tests and the
    main thread may supply full-SHA fixtures, but no implementation may
    silently infer a moving HEAD.
    """
    if materialization_commit is None:
        materialization_commit = new_materialization_commit
    elif new_materialization_commit is not None:
        _fail("materialization-commit", "new materialization commit was supplied twice")
    if type(predecessor_raw) is not bytes:
        _fail("predecessor-manifest", "v3 input must be exact v2 bytes")
    if materialization_commit is None:
        _fail("materialization-commit", "v3 requires an explicit new materialization commit")
    predecessor = validate_manifest(predecessor_raw)
    if predecessor.get("schema") != SCHEMA or predecessor.get("manifest_sha256") != EXPECTED_V2_MANIFEST_SHA256:
        _fail("predecessor-manifest", "v3 input must be the exact current v2 manifest")
    if previous_execution_tool_source_commit != EXPECTED_V2_EXECUTION_TOOL_SOURCE_COMMIT or predecessor.get("execution_tool_source_commit") != previous_execution_tool_source_commit:
        _fail("execution-tool-commit", "v3 old E does not match the exact v2 execution snapshot")
    for field, value in (("execution_tool_source_commit", execution_tool_source_commit), ("old_materialization_commit", old_materialization_commit), ("materialization_commit", materialization_commit)):
        if not _valid_commit(value):
            _fail("execution-tool-commit", f"{field} must be a full lowercase commit SHA")
    if execution_tool_source_commit in {predecessor["execution_tool_source_commit"], predecessor["candidate_source_commit"]}:
        _fail("execution-tool-commit", "v3 new E must be distinct from C and old E")
    if old_materialization_commit == materialization_commit:
        _fail("materialization-commit", "v3 old and new M commits must be distinct")

    # Authenticate the exact v2 bytes and the C-bound snapshot before adding
    # any successor fields.  The explicit chain is C -> old E -> old M -> new
    # E -> new M; each edge is checked independently.
    _validate_candidate_build_snapshot(repo, predecessor)
    for field, paths in (("runtime_tool_identities", RUNTIME_TOOLS), ("exact_runtime_tool_identities", LEGACY_EXACT_RUNTIME_TOOLS), ("provenance_tool_identities", PROVENANCE_TOOLS)):
        old_expected = _execution_tool_identities_from_commit(repo, previous_execution_tool_source_commit, paths)
        if predecessor.get(field) != old_expected:
            _fail("predecessor-manifest", f"v2 {field} differs from its exact old E snapshot")
    _assert_descendant_commit(repo, predecessor["candidate_source_commit"], previous_execution_tool_source_commit)
    _assert_descendant_commit(repo, previous_execution_tool_source_commit, old_materialization_commit)
    _assert_descendant_commit(repo, old_materialization_commit, execution_tool_source_commit)
    _assert_descendant_commit(repo, execution_tool_source_commit, materialization_commit)

    successor = json.loads(json.dumps(predecessor))
    successor.update({
        "schema": V3_SCHEMA,
        "manifest_sha256": None,
        "predecessor_manifest_sha256": predecessor["manifest_sha256"],
        "predecessor_v1_manifest_sha256": EXPECTED_V1_MANIFEST_SHA256,
        "predecessor_v2_inherited_sha256": predecessor["predecessor_inherited_sha256"],
        "previous_execution_tool_source_commit": previous_execution_tool_source_commit,
        "old_materialization_commit": old_materialization_commit,
        "materialization_commit": materialization_commit,
        "execution_tool_source_commit": execution_tool_source_commit,
        "runtime_tool_identities": _execution_tool_identities_from_commit(repo, execution_tool_source_commit, RUNTIME_TOOLS),
        "exact_runtime_tool_identities": _execution_tool_identities_from_commit(repo, execution_tool_source_commit, LEGACY_EXACT_RUNTIME_TOOLS),
        "provenance_tool_identities": _execution_tool_identities_from_commit(repo, execution_tool_source_commit, PROVENANCE_TOOLS),
        "experiment_closure_tool_identities": _execution_tool_identities_from_commit(repo, execution_tool_source_commit, EXPERIMENT_CLOSURE_TOOLS),
        "experiment_closure_schema": "ck.exp-0002.phase3.experiment-closure-1",
        "canonicalization": _v3_canonicalization(),
    })
    _seal(successor)
    validated = _validate_pure_manifest_v3(successor)
    _validate_candidate_build_snapshot(repo, validated)
    _validate_execution_commit_snapshot(repo, package, validated)
    observed_closure = _tool_identities(package, EXPERIMENT_CLOSURE_TOOLS)
    if observed_closure != validated["experiment_closure_tool_identities"]:
        _fail("execution-tool-drift", "current experiment closure tool differs from new E")
    return validated


def build_v4_successor_manifest(
    predecessor_raw: bytes,
    *,
    execution_tool_source_commit: str,
    materialization_commit: str | None = None,
    new_materialization_commit: str | None = None,
    old_materialization_commit: str | None = None,
    previous_execution_tool_source_commit: str | None = None,
    runtime_contract: Mapping[str, Any] | None = None,
    native_python_version: str | None = None,
    repo: Path = REPO,
    package: Path = PACKAGE,
) -> dict[str, Any]:
    """Build v4 from exact v3 bytes with an explicit Python runtime contract."""
    if materialization_commit is None:
        materialization_commit = new_materialization_commit
    elif new_materialization_commit is not None:
        _fail("materialization-commit", "new materialization commit was supplied twice")
    if type(predecessor_raw) is not bytes:
        _fail("predecessor-manifest", "v4 input must be exact v3 bytes")
    if materialization_commit is None:
        _fail("materialization-commit", "v4 requires an explicit new materialization commit")
    predecessor = validate_manifest(predecessor_raw)
    if predecessor.get("schema") != V3_SCHEMA or predecessor.get("manifest_sha256") != EXPECTED_V3_MANIFEST_SHA256:
        _fail("predecessor-manifest", "v4 input must be the exact current v3 manifest")
    if previous_execution_tool_source_commit is None:
        previous_execution_tool_source_commit = predecessor.get("execution_tool_source_commit")
    if old_materialization_commit is None:
        old_materialization_commit = predecessor.get("materialization_commit")
    if previous_execution_tool_source_commit != predecessor.get("execution_tool_source_commit"):
        _fail("execution-tool-commit", "v4 old E does not match the exact v3 execution snapshot")
    if old_materialization_commit != predecessor.get("materialization_commit"):
        _fail("materialization-commit", "v4 old M does not match the exact v3 materialization snapshot")
    for field, value in (
        ("execution_tool_source_commit", execution_tool_source_commit),
        ("old_materialization_commit", old_materialization_commit),
        ("materialization_commit", materialization_commit),
        ("previous_execution_tool_source_commit", previous_execution_tool_source_commit),
    ):
        if not _valid_commit(value):
            _fail("execution-tool-commit", f"{field} must be a full lowercase commit SHA")
    if execution_tool_source_commit in {predecessor["candidate_source_commit"], predecessor["execution_tool_source_commit"]}:
        _fail("execution-tool-commit", "v4 new E must be distinct from C and old E")
    if old_materialization_commit == materialization_commit:
        _fail("materialization-commit", "v4 old and new M commits must be distinct")
    runtime_contract = _build_python_runtime_contract(
        runtime_contract=runtime_contract,
        native_python_version=native_python_version,
    )

    # Authenticate v3's C-bound facts and old execution snapshot before adding
    # any v4 fields.  The current package may already contain the new E's
    # uncommitted bytes, so compare old tool identities to their committed E
    # without requiring them to match the moving working tree.
    _validate_candidate_build_snapshot(repo, predecessor)
    for field, paths in (
        ("runtime_tool_identities", RUNTIME_TOOLS),
        ("exact_runtime_tool_identities", LEGACY_EXACT_RUNTIME_TOOLS),
        ("provenance_tool_identities", PROVENANCE_TOOLS),
        ("experiment_closure_tool_identities", EXPERIMENT_CLOSURE_TOOLS),
    ):
        old_expected = _execution_tool_identities_from_commit(repo, previous_execution_tool_source_commit, paths)
        if predecessor.get(field) != old_expected:
            _fail("predecessor-manifest", f"v3 {field} differs from its exact old E snapshot")
    _assert_descendant_commit(repo, predecessor["candidate_source_commit"], previous_execution_tool_source_commit)
    _assert_descendant_commit(repo, previous_execution_tool_source_commit, old_materialization_commit)
    _assert_descendant_commit(repo, old_materialization_commit, execution_tool_source_commit)
    _assert_descendant_commit(repo, execution_tool_source_commit, materialization_commit)

    successor = json.loads(json.dumps(predecessor))
    successor.update({
        "schema": V4_SCHEMA,
        "manifest_sha256": None,
        "predecessor_manifest_sha256": predecessor["manifest_sha256"],
        "predecessor_v2_manifest_sha256": predecessor["predecessor_manifest_sha256"],
        "predecessor_v2_execution_tool_source_commit": predecessor["previous_execution_tool_source_commit"],
        "predecessor_v2_materialization_commit": predecessor["old_materialization_commit"],
        "previous_execution_tool_source_commit": previous_execution_tool_source_commit,
        "old_materialization_commit": old_materialization_commit,
        "materialization_commit": materialization_commit,
        "execution_tool_source_commit": execution_tool_source_commit,
        "runtime_tool_identities": _execution_tool_identities_from_commit(repo, execution_tool_source_commit, RUNTIME_TOOLS),
        "exact_runtime_tool_identities": _execution_tool_identities_from_commit(repo, execution_tool_source_commit, EXACT_RUNTIME_TOOLS),
        "provenance_tool_identities": _execution_tool_identities_from_commit(repo, execution_tool_source_commit, PROVENANCE_TOOLS),
        "experiment_closure_tool_identities": _execution_tool_identities_from_commit(repo, execution_tool_source_commit, EXPERIMENT_CLOSURE_TOOLS),
        "exact_python_runtime_contract": runtime_contract,
        "canonicalization": _v4_canonicalization(),
    })
    _seal(successor)
    validated = _validate_pure_manifest_v4(successor)
    _validate_candidate_build_snapshot(repo, validated)
    _validate_execution_commit_snapshot(repo, package, validated)
    if _tool_identities(package, EXPERIMENT_CLOSURE_TOOLS) != validated["experiment_closure_tool_identities"]:
        _fail("execution-tool-drift", "current experiment closure tool differs from new E")
    return validated


def build_v5_successor_manifest(
    predecessor_raw: bytes,
    *,
    execution_tool_source_commit: str,
    materialization_commit: str | None = None,
    new_materialization_commit: str | None = None,
    old_materialization_commit: str | None = None,
    previous_execution_tool_source_commit: str | None = None,
    runtime_contract: Mapping[str, Any] | None = None,
    repo: Path = REPO,
    package: Path = PACKAGE,
) -> dict[str, Any]:
    """Build v5 from exact v4 bytes and two current sidecar attestations.

    Runtime truth is never derived from this process.  The caller supplies a
    contract-2 mapping whose fixed sidecar paths must already exist under the
    package and whose canonical records are independently validated by the
    runtime-probe validator.
    """
    if materialization_commit is None:
        materialization_commit = new_materialization_commit
    elif new_materialization_commit is not None:
        _fail("materialization-commit", "new materialization commit was supplied twice")
    if type(predecessor_raw) is not bytes:
        _fail("predecessor-manifest", "v5 input must be exact v4 bytes")
    if materialization_commit is None:
        _fail("materialization-commit", "v5 requires an explicit new materialization commit")
    predecessor = validate_manifest(predecessor_raw)
    if predecessor.get("schema") != V4_SCHEMA or predecessor.get("manifest_sha256") != EXPECTED_V4_MANIFEST_SHA256:
        _fail("predecessor-manifest", "v5 input must be the exact current v4 manifest")
    if previous_execution_tool_source_commit is None:
        previous_execution_tool_source_commit = predecessor.get("execution_tool_source_commit")
    if old_materialization_commit is None:
        old_materialization_commit = predecessor.get("materialization_commit")
    if previous_execution_tool_source_commit != predecessor.get("execution_tool_source_commit"):
        _fail("execution-tool-commit", "v5 old E does not match the exact v4 execution snapshot")
    if old_materialization_commit != predecessor.get("materialization_commit"):
        _fail("materialization-commit", "v5 old M does not match the exact v4 materialization snapshot")
    for field, value in (("execution_tool_source_commit", execution_tool_source_commit), ("old_materialization_commit", old_materialization_commit), ("materialization_commit", materialization_commit), ("previous_execution_tool_source_commit", previous_execution_tool_source_commit)):
        if not _valid_commit(value):
            _fail("execution-tool-commit", f"{field} must be a full lowercase commit SHA")
    if execution_tool_source_commit in {predecessor["candidate_source_commit"], predecessor["execution_tool_source_commit"]}:
        _fail("execution-tool-commit", "v5 new E must be distinct from C and old E")
    if old_materialization_commit == materialization_commit:
        _fail("materialization-commit", "v5 old and new M commits must be distinct")
    if runtime_contract is None:
        _fail("runtime-contract", "v5 requires an explicit contract-2 runtime mapping")
    runtime_contract = _runtime_attestation_contract(package, runtime_contract)

    _validate_candidate_build_snapshot(repo, predecessor)
    for field, paths in (("runtime_tool_identities", RUNTIME_TOOLS), ("exact_runtime_tool_identities", EXACT_RUNTIME_TOOLS), ("provenance_tool_identities", PROVENANCE_TOOLS), ("experiment_closure_tool_identities", EXPERIMENT_CLOSURE_TOOLS)):
        old_expected = _execution_tool_identities_from_commit(repo, previous_execution_tool_source_commit, paths)
        if predecessor.get(field) != old_expected:
            _fail("predecessor-manifest", f"v4 {field} differs from its exact old E snapshot")
    _assert_descendant_commit(repo, predecessor["candidate_source_commit"], previous_execution_tool_source_commit)
    _assert_descendant_commit(repo, previous_execution_tool_source_commit, old_materialization_commit)
    _assert_descendant_commit(repo, old_materialization_commit, execution_tool_source_commit)
    _assert_descendant_commit(repo, execution_tool_source_commit, materialization_commit)

    successor = json.loads(json.dumps(predecessor))
    successor.update({
        "schema": V5_SCHEMA, "manifest_sha256": None,
        "predecessor_manifest_sha256": predecessor["manifest_sha256"],
        "predecessor_v1_manifest_sha256": predecessor["predecessor_v1_manifest_sha256"],
        "predecessor_v2_manifest_sha256": predecessor["predecessor_v2_manifest_sha256"],
        "predecessor_v2_inherited_sha256": predecessor["predecessor_v2_inherited_sha256"],
        "predecessor_v2_execution_tool_source_commit": predecessor["predecessor_v2_execution_tool_source_commit"],
        "predecessor_v2_materialization_commit": predecessor["predecessor_v2_materialization_commit"],
        "predecessor_v3_manifest_sha256": predecessor["predecessor_manifest_sha256"],
        "predecessor_v3_execution_tool_source_commit": predecessor["previous_execution_tool_source_commit"],
        "predecessor_v3_materialization_commit": predecessor["old_materialization_commit"],
        "predecessor_v4_manifest_sha256": predecessor["manifest_sha256"],
        "predecessor_exact_python_runtime_contract": predecessor["exact_python_runtime_contract"],
        "previous_execution_tool_source_commit": previous_execution_tool_source_commit,
        "old_materialization_commit": old_materialization_commit,
        "materialization_commit": materialization_commit,
        "execution_tool_source_commit": execution_tool_source_commit,
        "runtime_tool_identities": _execution_tool_identities_from_commit(repo, execution_tool_source_commit, RUNTIME_TOOLS),
        "exact_runtime_tool_identities": _execution_tool_identities_from_commit(repo, execution_tool_source_commit, EXACT_RUNTIME_TOOLS),
        "provenance_tool_identities": _execution_tool_identities_from_commit(repo, execution_tool_source_commit, V5_PROVENANCE_TOOLS),
        "experiment_closure_tool_identities": _execution_tool_identities_from_commit(repo, execution_tool_source_commit, EXPERIMENT_CLOSURE_TOOLS),
        "exact_python_runtime_contract": runtime_contract,
        "canonicalization": _v5_canonicalization(),
    })
    _seal(successor)
    validated = _validate_pure_manifest_v5(successor)
    _validate_candidate_build_snapshot(repo, validated)
    _validate_execution_commit_snapshot(repo, package, validated)
    if _tool_identities(package, EXPERIMENT_CLOSURE_TOOLS) != validated["experiment_closure_tool_identities"]:
        _fail("execution-tool-drift", "current experiment closure tool differs from new E")
    return validated


def check_historical_manifest(repo: Path = REPO, package: Path = PACKAGE, path: Path = MANIFEST) -> dict[str, Any]:
    """Check a v1 manifest only; retained for immutable historical validation."""
    recorded = _load_manifest(path)
    if recorded.get("schema") != V1_SCHEMA:
        _fail("historical-schema", "historical check requires a v1 freeze manifest")
    # The candidate commit remains authoritative after the later freeze commit,
    # but a check still requires a usable repository with a current HEAD.
    _resolve_source_commit(repo, None)
    _validate_candidate_commit_snapshot(repo, package, recorded)
    candidate_commit = recorded.get("candidate_source_commit")
    binaries = _validate_binary_slots(recorded.get("binaries"))
    _validate_bound_receipts(package, recorded, binaries)
    expected = generate_manifest(repo, package, binaries=binaries, source_commit=candidate_commit)
    if recorded != expected:
        _fail("manifest-drift", "manifest differs from current disk identities or canonical bindings")
    return recorded


def check_manifest(
    repo: Path = REPO,
    package: Path = PACKAGE,
    path: Path = MANIFEST,
    *,
    manifest_raw: bytes | None = None,
) -> dict[str, Any]:
    """Check the current successor freeze against its C/E/M chain."""
    recorded = _load_manifest(path, raw=manifest_raw)
    if recorded.get("schema") in {V3_SCHEMA, V4_SCHEMA, V5_SCHEMA}:
        current_materialization = _resolve_source_commit(repo, None)
        _assert_descendant_commit(repo, recorded.get("candidate_source_commit"), recorded.get("previous_execution_tool_source_commit"))
        _assert_descendant_commit(repo, recorded.get("previous_execution_tool_source_commit"), recorded.get("old_materialization_commit"))
        _assert_descendant_commit(repo, recorded.get("old_materialization_commit"), recorded.get("execution_tool_source_commit"))
        _assert_descendant_commit(repo, recorded.get("execution_tool_source_commit"), recorded.get("materialization_commit"))
        _assert_descendant_commit(repo, recorded.get("materialization_commit"), current_materialization)
        _validate_candidate_build_snapshot(repo, recorded)
        _validate_execution_commit_snapshot(repo, package, recorded)
        _validate_binary_slots(recorded.get("binaries"))
        _validate_bound_receipts(package, recorded, _validate_binary_slots(recorded.get("binaries")))
        _validate_current_candidate_build_inputs(repo, package, recorded)
        if _tool_identities(package, EXPERIMENT_CLOSURE_TOOLS) != recorded.get("experiment_closure_tool_identities"):
            _fail("execution-tool-drift", "current experiment closure tool differs from new E")
        if recorded.get("schema") == V5_SCHEMA:
            _runtime_attestation_contract(package, recorded["exact_python_runtime_contract"])
        return recorded
    if recorded.get("schema") != SCHEMA:
        _fail("current-schema", "current freeze check requires the v2, v3, or v4 successor manifest")
    _resolve_source_commit(repo, None)
    _validate_candidate_build_snapshot(repo, recorded)
    _validate_execution_commit_snapshot(repo, package, recorded)
    binaries = _validate_binary_slots(recorded.get("binaries"))
    _validate_bound_receipts(package, recorded, binaries)
    _validate_current_candidate_build_inputs(repo, package, recorded)
    return recorded


def _rename_exchange(first: Path, second: Path) -> None:
    """Atomically exchange two Linux directory entries or fail closed."""
    try:
        library = ctypes.CDLL(None, use_errno=True)
        renameat2 = library.renameat2
    except (OSError, AttributeError) as error:
        raise FreezeManifestError("manifest-write", "atomic rename exchange is unavailable") from error
    renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    renameat2.restype = ctypes.c_int
    at_fdcwd = -100
    rename_exchange = 2
    if renameat2(at_fdcwd, os.fsencode(first), at_fdcwd, os.fsencode(second), rename_exchange) != 0:
        error_number = ctypes.get_errno()
        raise FreezeManifestError("manifest-write", f"atomic rename exchange failed: {os.strerror(error_number)}")


def _rename_noreplace(first: Path, second: Path) -> None:
    """Atomically publish an absent destination without replacement."""
    try:
        library = ctypes.CDLL(None, use_errno=True)
        renameat2 = library.renameat2
    except (OSError, AttributeError) as error:
        raise FreezeManifestError("manifest-write", "atomic no-replace rename is unavailable") from error
    renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    renameat2.restype = ctypes.c_int
    at_fdcwd = -100
    rename_noreplace = 1
    if renameat2(at_fdcwd, os.fsencode(first), at_fdcwd, os.fsencode(second), rename_noreplace) != 0:
        error_number = ctypes.get_errno()
        raise FreezeManifestError("manifest-write", f"atomic no-replace rename failed: {os.strerror(error_number)}")


def _same_exchanged_snapshot(
    observed: tuple[bytes, tuple[int, int, int, int, int, int, int]],
    expected: tuple[bytes, tuple[int, int, int, int, int, int, int]],
) -> bool:
    # Linux rename updates ctime on the exchanged inodes.  The retained
    # dev/inode, mode, link count, size, mtime, and exact bytes still identify
    # the destination that occupied the CAS slot at the exchange point.
    return observed[0] == expected[0] and observed[1][:-1] == expected[1][:-1]


def _fsync_directory(path: Path) -> None:
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    except OSError as error:
        raise FreezeManifestError("manifest-write", "cannot open manifest directory for fsync") from error
    try:
        os.fsync(descriptor)
    except OSError as error:
        raise FreezeManifestError("manifest-write", "cannot fsync manifest directory") from error
    finally:
        try:
            os.close(descriptor)
        except OSError as error:
            raise FreezeManifestError("manifest-write", "cannot close fsynced manifest directory") from error


def _atomic_write_manifest(
    value: Mapping[str, Any],
    path: Path,
    *,
    expected_destination_snapshot: tuple[bytes, tuple[int, int, int, int, int, int, int]] | None = None,
    expect_destination_absent: bool = False,
) -> None:
    """Write canonical bytes without exposing a partial or bound overwrite."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        existing_info = path.lstat()
    except FileNotFoundError:
        existing_info = None
    except OSError as error:
        raise FreezeManifestError("manifest-write", str(path)) from error
    if existing_info is not None:
        if expect_destination_absent:
            _fail("manifest-write", "destination appeared after the caller observed absence")
        if not stat.S_ISREG(existing_info.st_mode) or stat.S_ISLNK(existing_info.st_mode) or stat.S_IMODE(existing_info.st_mode) != 0o644 or existing_info.st_nlink != 1:
            _fail("manifest-write", "manifest path must be a mode-0644 single-link regular file")
        try:
            existing_raw, existing_identity = _read_manifest_snapshot(path)
            existing = validate_manifest(existing_raw)
            existing_binaries = _validate_binary_slots(existing.get("binaries"))
        except FreezeManifestError as error:
            raise FreezeManifestError("manifest-write", f"existing manifest is not safely replaceable: {error.code}") from error
        existing_snapshot = (existing_raw, existing_identity)
        if expected_destination_snapshot is not None and existing_snapshot != expected_destination_snapshot:
            _fail("manifest-write", "destination differs from the caller-validated snapshot")
        if all(slot["status"] == "bound" for slot in existing_binaries.values()):
            successor_allowed = (
                expected_destination_snapshot is not None
                and (
                    (existing.get("schema") == V1_SCHEMA and value.get("schema") == SCHEMA)
                    or (existing.get("schema") == SCHEMA and value.get("schema") == V3_SCHEMA)
                    or (existing.get("schema") == V3_SCHEMA and value.get("schema") == V4_SCHEMA)
                    or (existing.get("schema") == V4_SCHEMA and value.get("schema") == V5_SCHEMA)
                )
                and value.get("predecessor_manifest_sha256") == existing.get("manifest_sha256")
            )
            if not successor_allowed:
                _fail("manifest-finalized", "refusing to overwrite an already bound freeze manifest")
        conditional_snapshot = existing_snapshot
    else:
        if expected_destination_snapshot is not None:
            _fail("manifest-write", "expected destination disappeared before publication")
        conditional_snapshot = None
    raw = _canonical(value)
    temporary: Path | None = None
    preserve_temporary = False
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            os.fchmod(stream.fileno(), 0o644)
            temporary_info = os.fstat(stream.fileno())
            if not stat.S_ISREG(temporary_info.st_mode) or stat.S_IMODE(temporary_info.st_mode) != 0o644 or temporary_info.st_nlink != 1:
                _fail("manifest-write", "temporary manifest is not a mode-0644 single-link regular file")
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        if conditional_snapshot is None:
            _rename_noreplace(temporary, path)
            temporary = None
        else:
            # RENAME_EXCHANGE is the compare-and-swap linearization point.  It
            # never discards the displaced destination: that entry moves to
            # ``temporary`` atomically, where it can be compared with the
            # exact caller-validated destination.  On mismatch, exchange again
            # to restore it.
            _rename_exchange(temporary, path)
            try:
                displaced_snapshot = _read_manifest_snapshot(temporary)
                if not _same_exchanged_snapshot(displaced_snapshot, conditional_snapshot):
                    _fail("manifest-write", "destination changed before conditional exchange")
            except FreezeManifestError as detection_error:
                try:
                    _rename_exchange(path, temporary)
                except FreezeManifestError as rollback_error:
                    preserve_temporary = True
                    raise FreezeManifestError(
                        "manifest-write",
                        f"destination changed and rollback failed; displaced entry preserved at {temporary}",
                    ) from rollback_error
                raise detection_error
        try:
            _fsync_directory(path.parent)
        except FreezeManifestError as publication_error:
            if conditional_snapshot is None:
                # The no-replace publication is already visible and there is
                # no old entry that can be restored with a conditional atomic
                # operation. Treat directory sync as best-effort here so the
                # reported success matches the visible new state.
                return
            try:
                _rename_exchange(path, temporary)
            except FreezeManifestError as rollback_error:
                preserve_temporary = True
                raise FreezeManifestError(
                    "manifest-write",
                    f"directory sync failed and rollback failed; displaced entry preserved at {temporary}",
                ) from rollback_error
            try:
                _fsync_directory(path.parent)
            except FreezeManifestError as rollback_sync_error:
                preserve_temporary = True
                raise FreezeManifestError(
                    "manifest-write",
                    f"directory sync failed and rollback durability is unknown; replacement preserved at {temporary}",
                ) from rollback_sync_error
            raise publication_error
        if conditional_snapshot is not None:
            # The new entry is durable before the displaced old entry is
            # removed. Cleanup failure cannot invalidate successful
            # publication; retaining the old entry is recoverable.
            try:
                temporary.unlink()
            except OSError:
                preserve_temporary = True
            else:
                temporary = None
                try:
                    _fsync_directory(path.parent)
                except FreezeManifestError:
                    # Publication was already durable. Failure to durably
                    # record cleanup can only resurrect the displaced temp
                    # entry after a crash, so it must not turn success into a
                    # false publication failure.
                    pass
    except OSError as error:
        raise FreezeManifestError("manifest-write", str(path)) from error
    finally:
        if temporary is not None and not preserve_temporary:
            try:
                temporary.unlink()
            except OSError:
                pass


def finalize_from_receipts(path: Path, receipt_paths: list[Path], *, repo: Path = REPO, package: Path = PACKAGE) -> dict[str, Any]:
    """Bind exactly one WSL and one native receipt, without executing anything."""
    if len(receipt_paths) != 2:
        _fail("build-receipt", "exactly two build receipts (WSL and native) are required")
    _resolve_source_commit(repo, None)
    baseline_snapshot = _read_manifest_snapshot(path)
    baseline = validate_manifest(baseline_snapshot[0])
    candidate_commit = baseline.get("candidate_source_commit")
    if not _valid_commit(candidate_commit):
        _fail("source-commit", "pre-freeze manifest candidate source commit is invalid")
    _validate_candidate_commit_snapshot(repo, package, baseline)
    current = _validate_binary_slots(baseline.get("binaries"))
    if any(slot["status"] == "bound" for slot in current.values()):
        _fail("build-receipt", "finalization requires an unbound pre-freeze manifest")
    current_baseline = generate_manifest(repo, package, binaries=current, source_commit=candidate_commit)
    if baseline != current_baseline:
        _fail("manifest-drift", "pre-freeze manifest differs from current frozen inputs")
    expected_closure = baseline.get("candidate_closure")
    if not isinstance(expected_closure, Mapping):
        _fail("build-receipt", "manifest candidate closure is missing")
    seen: set[str] = set()
    commits: set[str] = set()
    facts: list[Mapping[str, Any]] = []
    for receipt_path in receipt_paths:
        selector, binding, commit, value = _load_build_receipt(receipt_path, package, expected_closure, baseline)
        if selector in seen:
            _fail("build-receipt", f"duplicate receipt selector {selector}")
        if commit != candidate_commit:
            _fail("source-commit", "build receipt source commit differs from candidate source commit")
        seen.add(selector)
        commits.add(commit)
        facts.append(value["build"])
        current[selector] = binding
    if seen != set(SELECTORS):
        _fail("build-receipt", "both frozen platform selectors are required")
    if len(commits) != 1:
        _fail("build-receipt", "WSL and native receipts do not use the same full source commit")
    if _dependency_logical(facts[0]["dependency_closure"]) != _dependency_logical(facts[1]["dependency_closure"]):
        _fail("build-receipt", "WSL and native receipts do not share dependency closure")
    if _vendor_logical(facts[0]["vendor_closure"]) != _vendor_logical(facts[1]["vendor_closure"]):
        _fail("build-receipt", "WSL and native receipts do not share vendor closure")
    sealed = generate_manifest(repo, package, binaries=current, source_commit=candidate_commit)
    _atomic_write_manifest(sealed, path, expected_destination_snapshot=baseline_snapshot)
    return sealed


def write_manifest(
    value: Mapping[str, Any],
    path: Path = MANIFEST,
    *,
    repo: Path = REPO,
    package: Path = PACKAGE,
) -> None:
    """Write only an exact generated manifest, never arbitrary caller JSON."""
    try:
        path.lstat()
    except FileNotFoundError:
        destination_snapshot = None
        destination_was_absent = True
    except OSError as error:
        raise FreezeManifestError("manifest-write", str(path)) from error
    else:
        destination_snapshot = _read_manifest_snapshot(path)
        destination_was_absent = False
    if not isinstance(value, dict):
        _fail("manifest-write", "supplied manifest must be an object")
    try:
        supplied_self_hash = _self_hash(value)
    except (TypeError, ValueError, UnicodeEncodeError, RecursionError) as error:
        raise FreezeManifestError("manifest-write", "supplied manifest is not canonical JSON data") from error
    if value.get("manifest_sha256") != supplied_self_hash:
        _fail("manifest-self-hash", "supplied manifest self hash does not match")
    candidate_commit = value.get("candidate_source_commit")
    binaries = _validate_binary_slots(value.get("binaries"))
    expected = generate_manifest(repo, package, binaries=binaries, source_commit=candidate_commit)
    if value != expected:
        _fail("manifest-drift", "supplied manifest differs from the generated freeze contract")
    _atomic_write_manifest(
        expected,
        path,
        expected_destination_snapshot=destination_snapshot,
        expect_destination_absent=destination_was_absent,
    )


def write_successor_manifest(
    path: Path,
    execution_tool_source_commit: str,
    *,
    repo: Path = REPO,
    package: Path = PACKAGE,
) -> dict[str, Any]:
    """Replace the exact bound v1 once; an existing v2 is never overwritten."""
    predecessor_snapshot = _read_manifest_snapshot(path)
    predecessor_raw = predecessor_snapshot[0]
    predecessor = validate_manifest(predecessor_raw)
    if predecessor.get("schema") != V1_SCHEMA:
        _fail("manifest-finalized", "successor creation requires the exact bound v1 manifest")
    successor = build_successor_manifest(
        predecessor_raw,
        execution_tool_source_commit=execution_tool_source_commit,
        repo=repo,
        package=package,
    )
    _atomic_write_manifest(successor, path, expected_destination_snapshot=predecessor_snapshot)
    return successor


def write_v3_successor_manifest(
    path: Path,
    execution_tool_source_commit: str,
    *,
    materialization_commit: str | None = None,
    new_materialization_commit: str | None = None,
    old_materialization_commit: str = EXPECTED_V2_MATERIALIZATION_COMMIT,
    previous_execution_tool_source_commit: str = EXPECTED_V2_EXECUTION_TOOL_SOURCE_COMMIT,
    repo: Path = REPO,
    package: Path = PACKAGE,
) -> dict[str, Any]:
    """Atomically replace exact v2 once with a v3 successor."""
    predecessor_snapshot = _read_manifest_snapshot(path)
    predecessor = validate_manifest(predecessor_snapshot[0])
    if predecessor.get("schema") != SCHEMA or predecessor.get("manifest_sha256") != EXPECTED_V2_MANIFEST_SHA256:
        _fail("manifest-finalized", "v3 creation requires the exact current v2 manifest")
    successor = build_v3_successor_manifest(
        predecessor_snapshot[0],
        execution_tool_source_commit=execution_tool_source_commit,
        materialization_commit=materialization_commit,
        new_materialization_commit=new_materialization_commit,
        old_materialization_commit=old_materialization_commit,
        previous_execution_tool_source_commit=previous_execution_tool_source_commit,
        repo=repo,
        package=package,
    )
    _atomic_write_manifest(successor, path, expected_destination_snapshot=predecessor_snapshot)
    return successor


def write_v4_successor_manifest(
    path: Path,
    execution_tool_source_commit: str,
    *,
    materialization_commit: str | None = None,
    new_materialization_commit: str | None = None,
    native_python_version: str | None = None,
    runtime_contract: Mapping[str, Any] | None = None,
    old_materialization_commit: str | None = None,
    previous_execution_tool_source_commit: str | None = None,
    repo: Path = REPO,
    package: Path = PACKAGE,
) -> dict[str, Any]:
    """Atomically replace the exact v3 freeze with a v4 runtime-bound successor."""
    predecessor_snapshot = _read_manifest_snapshot(path)
    predecessor = validate_manifest(predecessor_snapshot[0])
    if predecessor.get("schema") != V3_SCHEMA or predecessor.get("manifest_sha256") != EXPECTED_V3_MANIFEST_SHA256:
        _fail("manifest-finalized", "v4 creation requires the exact current v3 manifest")
    successor = build_v4_successor_manifest(
        predecessor_snapshot[0],
        execution_tool_source_commit=execution_tool_source_commit,
        materialization_commit=materialization_commit,
        new_materialization_commit=new_materialization_commit,
        runtime_contract=runtime_contract,
        native_python_version=native_python_version,
        old_materialization_commit=old_materialization_commit,
        previous_execution_tool_source_commit=previous_execution_tool_source_commit,
        repo=repo,
        package=package,
    )
    _atomic_write_manifest(successor, path, expected_destination_snapshot=predecessor_snapshot)
    return successor


def write_v5_successor_manifest(
    path: Path,
    execution_tool_source_commit: str,
    *,
    materialization_commit: str | None = None,
    new_materialization_commit: str | None = None,
    runtime_contract: Mapping[str, Any] | None = None,
    old_materialization_commit: str | None = None,
    previous_execution_tool_source_commit: str | None = None,
    repo: Path = REPO,
    package: Path = PACKAGE,
) -> dict[str, Any]:
    """Atomically replace exact v4 bytes with a v5 runtime-attested successor."""
    predecessor_snapshot = _read_manifest_snapshot(path)
    predecessor = validate_manifest(predecessor_snapshot[0])
    if predecessor.get("schema") != V4_SCHEMA or predecessor.get("manifest_sha256") != EXPECTED_V4_MANIFEST_SHA256:
        _fail("manifest-finalized", "v5 creation requires the exact current v4 manifest")
    successor = build_v5_successor_manifest(
        predecessor_snapshot[0], execution_tool_source_commit=execution_tool_source_commit,
        materialization_commit=materialization_commit, new_materialization_commit=new_materialization_commit,
        runtime_contract=runtime_contract, old_materialization_commit=old_materialization_commit,
        previous_execution_tool_source_commit=previous_execution_tool_source_commit, repo=repo, package=package,
    )
    _atomic_write_manifest(successor, path, expected_destination_snapshot=predecessor_snapshot)
    return successor


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="generate or check the execution-disabled Phase 3 freeze manifest")
    parser.add_argument("--repo", type=Path, default=REPO)
    parser.add_argument("--package", type=Path, default=PACKAGE)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--finalize", type=Path, nargs=2, metavar=("WSL_RECEIPT", "NATIVE_RECEIPT"))
    parser.add_argument("--successor", metavar="EXECUTION_TOOL_COMMIT")
    parser.add_argument("--successor-v3", nargs=2, metavar=("EXECUTION_TOOL_COMMIT", "MATERIALIZATION_COMMIT"))
    parser.add_argument(
        "--successor-v4", nargs=4,
        metavar=("EXECUTION_TOOL_COMMIT", "MATERIALIZATION_COMMIT", "NATIVE_PYTHON_VERSION", "RUNTIME_CONTRACT_JSON"),
        help="create v4 using a canonical exact_python_runtime_contract JSON file",
    )
    parser.add_argument(
        "--successor-v5", nargs=3,
        metavar=("EXECUTION_TOOL_COMMIT", "MATERIALIZATION_COMMIT", "RUNTIME_CONTRACT_JSON"),
        help="create v5 using two current runtime-attestation sidecars and contract-2 JSON",
    )
    args = parser.parse_args(argv)
    try:
        if args.check:
            check_manifest(args.repo.resolve(), args.package.resolve(), args.manifest.resolve())
            print("PHASE 3 FREEZE MANIFEST CHECK OK")
        elif args.successor_v3:
            successor = write_v3_successor_manifest(
                args.manifest.resolve(),
                args.successor_v3[0],
                materialization_commit=args.successor_v3[1],
                repo=args.repo.resolve(),
                package=args.package.resolve(),
            )
            print(f"PHASE 3 FREEZE MANIFEST V3 SUCCESSOR CREATED: {successor['manifest_sha256']}")
        elif args.successor_v4:
            successor = write_v4_successor_manifest(
                args.manifest.resolve(),
                args.successor_v4[0],
                materialization_commit=args.successor_v4[1],
                native_python_version=args.successor_v4[2],
                runtime_contract=_load_runtime_contract_json(Path(args.successor_v4[3]).resolve()),
                repo=args.repo.resolve(),
                package=args.package.resolve(),
            )
            print(f"PHASE 3 FREEZE MANIFEST V4 SUCCESSOR CREATED: {successor['manifest_sha256']}")
        elif args.successor_v5:
            successor = write_v5_successor_manifest(
                args.manifest.resolve(), args.successor_v5[0], materialization_commit=args.successor_v5[1],
                runtime_contract=_load_runtime_contract_json(Path(args.successor_v5[2]).resolve()),
                repo=args.repo.resolve(), package=args.package.resolve(),
            )
            print(f"PHASE 3 FREEZE MANIFEST V5 SUCCESSOR CREATED: {successor['manifest_sha256']}")
        elif args.successor:
            successor = write_successor_manifest(
                args.manifest.resolve(),
                args.successor,
                repo=args.repo.resolve(),
                package=args.package.resolve(),
            )
            print(f"PHASE 3 FREEZE MANIFEST SUCCESSOR CREATED: {successor['manifest_sha256']}")
        elif args.finalize:
            finalized = finalize_from_receipts(args.manifest.resolve(), [item.resolve() for item in args.finalize], repo=args.repo.resolve(), package=args.package.resolve())
            print(f"PHASE 3 FREEZE MANIFEST FINALIZED: {finalized['readiness']['materialization_state']}")
        else:
            write_manifest(
                generate_manifest(args.repo.resolve(), args.package.resolve()),
                args.manifest.resolve(),
                repo=args.repo.resolve(),
                package=args.package.resolve(),
            )
            print("PHASE 3 FREEZE MANIFEST GENERATED: execution remains disabled")
    except FreezeManifestError as error:
        print(f"PHASE 3 FREEZE MANIFEST FAILED: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["V1_SCHEMA", "SCHEMA", "V2_SCHEMA", "V3_SCHEMA", "V4_SCHEMA", "V5_SCHEMA", "CURRENT_SCHEMA", "PHASE_ID", "FreezeManifestError", "validate_manifest", "generate_manifest", "build_successor_manifest", "build_v3_successor_manifest", "build_v4_successor_manifest", "build_v5_successor_manifest", "check_historical_manifest", "check_manifest", "finalize_from_receipts", "write_manifest", "write_successor_manifest", "write_v3_successor_manifest", "write_v4_successor_manifest", "write_v5_successor_manifest", "MANIFEST", "PACKAGE", "REPO"]

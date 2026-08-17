#!/usr/bin/env python3
"""Fail-closed, one-shot execution and receipt wrapper for EXP-0002 phase one.

The wrapper owns provenance, build, and receipt gates.  It deliberately does
not implement a second corpus runner: after the gates pass it invokes the
authoritative ``run_adapter.py`` exactly once and validates its result without
rerunning any corpus case.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import selectors
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = SCRIPT_DIR.parent
REPOSITORY_ROOT = PACKAGE_DIR.parents[1]
MANIFEST = PACKAGE_DIR / "corpora" / "manifest.json"
RUNNER = SCRIPT_DIR / "run_adapter.py"
CANDIDATE_MANIFEST = PACKAGE_DIR / "candidate" / "Cargo.toml"
CANDIDATE_TARGET = "x86_64-unknown-linux-gnu"
CANDIDATE_BINARY = "exp-0002-numeric-frame-profile-candidate"
CANDIDATE_PATH = PACKAGE_DIR / "candidate" / "target" / CANDIDATE_TARGET / "debug" / CANDIDATE_BINARY
ACKNOWLEDGEMENT = "RUN-EXP-0002-PHASE1"
ATTEMPT_RE = re.compile(r"attempt-[0-9]{3,}")
FULL_COMMIT_RE = re.compile(r"[0-9a-f]{40}")
RECEIPT_SCHEMA = "ck.exp-0002.phase1-run-receipt-1"
RESULT_SCHEMA = "ck.exp-0002.numeric-corpus-result-1"
EVALUATION_BINDING = "ck.exp-0002.phase1-persistent-conformance-v1"
TECHNOLOGY_RESULT = "none"
ROLES = ("development", "held-out", "adversarial")
CASE_CLASSIFICATIONS = ("fail", "inconclusive", "incomplete", "pass", "unsupported")
ENV_ALLOWLIST = (
    "RUSTFLAGS",
    "CARGO_ENCODED_RUSTFLAGS",
    "CARGO_BUILD_TARGET",
    "CARGO_TARGET_DIR",
    "CARGO_INCREMENTAL",
    "RUSTC_WRAPPER",
    "RUSTC_WORKSPACE_WRAPPER",
    "RUSTUP_TOOLCHAIN",
)
MAX_SUBPROCESS_OUTPUT = 64 * 1024
MAX_ERROR_TEXT = 4096
MAX_RESULT_BYTES = 4 * 1024 * 1024
MAX_ARTIFACT_BYTES = 256 * 1024 * 1024
MAX_RECEIPT_BYTES = 1024 * 1024
COMMAND_DEADLINE_SECONDS = 180.0
OBSERVATION_DEADLINE_SECONDS = 5.0

# Import the runner's strict JSON/schema helpers without making this wrapper a
# second runner.  Keeping the import local to this package also lets the unit
# tests construct synthetic manifests and fake results without importing the
# authoritative command as a subprocess.
sys.path.insert(0, str(SCRIPT_DIR))
from runner_common import (  # noqa: E402
    ProtocolError,
    _duplicate_rejector,
    _reject_constant,
)
from runner_schema import load_manifest  # noqa: E402


class WrapperError(RuntimeError):
    """A wrapper gate failed; the authoritative runner was not necessarily run."""


@dataclass(frozen=True)
class CommandResult:
    argv: tuple[str, ...]
    exit_code: int | None
    stdout: bytes
    stderr: bytes
    timed_out: bool = False
    output_bound_exceeded: bool = False

    def as_receipt(self) -> dict[str, Any]:
        return {
            "argv": list(self.argv),
            "exit_code": self.exit_code,
            "timed_out": self.timed_out,
            "output_bound_exceeded": self.output_bound_exceeded,
            "stdout_bytes": len(self.stdout),
            "stdout_sha256": hashlib.sha256(self.stdout).hexdigest(),
            "stdout_text": _bounded_text(self.stdout),
            "stderr_bytes": len(self.stderr),
            "stderr_sha256": hashlib.sha256(self.stderr).hexdigest(),
            "stderr_text": _bounded_text(self.stderr),
        }


def _bounded_text(payload: bytes) -> str:
    return payload[:MAX_ERROR_TEXT].decode("utf-8", errors="replace")


def _strict_json(raw: bytes, *, cap: int) -> Any:
    if len(raw) > cap:
        raise WrapperError(f"JSON exceeds {cap}-byte cap")
    try:
        text = raw.decode("utf-8", errors="strict")
        if text.startswith("\ufeff"):
            raise WrapperError("JSON BOM is not permitted")
        return json.loads(text, object_pairs_hook=_duplicate_rejector, parse_constant=_reject_constant)
    except WrapperError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ProtocolError) as error:
        raise WrapperError(f"invalid strict JSON: {error}") from error


def _file_sha256(path: Path, *, cap: int = MAX_RESULT_BYTES) -> str:
    if path.is_symlink() or not path.is_file():
        raise WrapperError(f"not a regular non-symlink file: {path}")
    digest = hashlib.sha256()
    total = 0
    try:
        with path.open("rb") as stream:
            while True:
                chunk = stream.read(min(1024 * 1024, cap - total + 1))
                if not chunk:
                    break
                total += len(chunk)
                if total > cap:
                    raise WrapperError(f"file exceeds {cap}-byte cap: {path}")
                digest.update(chunk)
    except OSError as error:
        raise WrapperError(f"cannot hash {path}: {error}") from error
    return digest.hexdigest()


def _kill_process(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
    except (OSError, ProcessLookupError):
        try:
            process.kill()
        except OSError:
            pass


def _run_command(
    argv: Sequence[str],
    *,
    cwd: Path,
    env: Mapping[str, str] | None = None,
    timeout: float = COMMAND_DEADLINE_SECONDS,
    output_cap: int = MAX_SUBPROCESS_OUTPUT,
) -> CommandResult:
    """Run one bounded command without shell/encoded-command indirection."""

    command = tuple(str(part) for part in argv)
    try:
        process = subprocess.Popen(
            list(command),
            cwd=str(cwd),
            env=dict(env) if env is not None else None,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
    except OSError as error:
        return CommandResult(command, None, b"", str(error).encode("utf-8", errors="replace"))

    assert process.stdout is not None and process.stderr is not None
    for stream in (process.stdout, process.stderr):
        os.set_blocking(stream.fileno(), False)
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ, "stdout")
    selector.register(process.stderr, selectors.EVENT_READ, "stderr")
    output = {"stdout": bytearray(), "stderr": bytearray()}
    deadline = time.monotonic() + timeout
    timed_out = False
    bound_exceeded = False
    try:
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timed_out = True
                _kill_process(process)
                break
            for key, _mask in selector.select(min(0.05, remaining)):
                stream = key.fileobj
                label = key.data
                try:
                    chunk = os.read(stream.fileno(), min(8192, output_cap + 1 - len(output[label])))
                except BlockingIOError:
                    continue
                if not chunk:
                    selector.unregister(stream)
                    continue
                output[label].extend(chunk)
                if len(output[label]) > output_cap:
                    bound_exceeded = True
                    _kill_process(process)
                    break
            if timed_out or bound_exceeded:
                break
        # Drain only the bounded tail after a forced termination, then close.
        if timed_out or bound_exceeded:
            drain_deadline = time.monotonic() + 0.5
            while selector.get_map() and time.monotonic() < drain_deadline:
                for key, _mask in selector.select(0.02):
                    try:
                        chunk = os.read(key.fileobj.fileno(), min(8192, output_cap + 1 - len(output[key.data])))
                    except (BlockingIOError, OSError):
                        chunk = b""
                    if not chunk:
                        try:
                            selector.unregister(key.fileobj)
                        except KeyError:
                            pass
                    else:
                        output[key.data].extend(chunk)
                        if len(output[key.data]) > output_cap:
                            output[key.data][:] = output[key.data][:output_cap]
    finally:
        selector.close()
        if process.poll() is None:
            _kill_process(process)
        try:
            process.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            _kill_process(process)
            process.wait(timeout=0.5)
        process.stdout.close()
        process.stderr.close()
    return CommandResult(
        command,
        process.returncode,
        bytes(output["stdout"][:output_cap]),
        bytes(output["stderr"][:output_cap]),
        timed_out=timed_out,
        output_bound_exceeded=bound_exceeded,
    )


def source_snapshot(root: Path) -> dict[str, Any]:
    """Return the exact HEAD and all three cleanliness dimensions."""
    root = Path(root)
    commit_result = _run_command(["git", "rev-parse", "--verify", "HEAD^{commit}"], cwd=root, timeout=5.0, output_cap=128)
    try:
        commit = commit_result.stdout.decode("utf-8", errors="strict").strip()
    except UnicodeDecodeError as error:
        raise WrapperError("source commit output is not UTF-8") from error
    if commit_result.exit_code != 0 or commit_result.timed_out or commit_result.output_bound_exceeded or commit_result.stderr or not FULL_COMMIT_RE.fullmatch(commit):
        raise WrapperError("cannot resolve full source commit C")

    def no_output_probe(argv: Sequence[str]) -> tuple[bool, bool]:
        probe = _run_command(argv, cwd=root, timeout=5.0, output_cap=1)
        complete = not probe.timed_out and not probe.output_bound_exceeded and not probe.stdout and not probe.stderr
        return complete, probe.exit_code == 0

    tracked_covered, tracked_clean = no_output_probe(["git", "diff", "--quiet"])
    staged_covered, staged_clean = no_output_probe(["git", "diff", "--cached", "--quiet"])
    untracked_probe = _run_command(["git", "ls-files", "--others", "--exclude-standard", "-z"], cwd=root, timeout=5.0, output_cap=MAX_SUBPROCESS_OUTPUT)
    untracked_covered = not untracked_probe.timed_out and not untracked_probe.output_bound_exceeded and not untracked_probe.stderr and untracked_probe.exit_code == 0
    untracked: list[str] = []
    if untracked_covered:
        try:
            decoded = untracked_probe.stdout.decode("utf-8", errors="strict")
            if decoded and not decoded.endswith("\0"):
                untracked_covered = False
            else:
                untracked = [path for path in decoded.split("\0") if path]
        except UnicodeDecodeError:
            untracked_covered = False
    if not untracked_covered:
        untracked = []
    return {
        "commit": commit,
        "clean": tracked_covered and staged_covered and untracked_covered and tracked_clean and staged_clean and not untracked,
        "tracked_clean": tracked_covered and tracked_clean,
        "staged_clean": staged_covered and staged_clean,
        "untracked_clean": untracked_covered and not untracked,
        "untracked_paths": untracked[:128],
        "untracked_covered": tracked_covered and staged_covered and untracked_covered,
    }


def validate_attempt_id(value: str) -> str:
    if not ATTEMPT_RE.fullmatch(value):
        raise WrapperError("attempt ID must match attempt-[0-9]{3,} (for example attempt-001)")
    return value


def attempt_path(root: Path, commit: str, attempt_id: str) -> Path:
    validate_attempt_id(attempt_id)
    if not FULL_COMMIT_RE.fullmatch(commit):
        raise WrapperError("source commit must be a full 40-character lowercase commit")
    return root / "experiments" / "EXP-0002-numeric-frame-profile" / "results" / "phase1" / commit / attempt_id


def _validate_path(path: Path, base: Path, label: str, *, kind: str) -> Path:
    """Validate containment and reject symlinks in every existing component."""

    raw = Path(path)
    base_raw = Path(base)
    try:
        base_resolved = base_raw.resolve(strict=True)
        lexical = Path(os.path.abspath(raw))
        lexical_base = Path(os.path.abspath(base_raw))
        lexical.relative_to(lexical_base)
        resolved = raw.resolve(strict=False)
        resolved.relative_to(base_resolved)
    except (OSError, RuntimeError, ValueError) as error:
        raise WrapperError(f"{label} escapes its allowed root or has an invalid ancestry") from error
    current = lexical_base
    for component in lexical.relative_to(lexical_base).parts:
        current /= component
        if os.path.lexists(current):
            if current.is_symlink():
                raise WrapperError(f"{label} ancestry contains a symlink: {current}")
            if current != lexical and not current.is_dir():
                raise WrapperError(f"{label} ancestry is not a directory: {current}")
    if kind == "dir" and os.path.lexists(lexical) and (lexical.is_symlink() or not lexical.is_dir()):
        raise WrapperError(f"{label} is not a regular directory")
    if kind == "file" and os.path.lexists(lexical) and (lexical.is_symlink() or not lexical.is_file()):
        raise WrapperError(f"{label} is not a regular file")
    return resolved


def _validate_fixed_paths(root: Path) -> dict[str, Path]:
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise WrapperError("repository root is not a directory")
    package = _validate_path(PACKAGE_DIR, root, "experiment package", kind="dir")
    manifest = _validate_path(MANIFEST, package, "authoritative manifest", kind="file")
    runner = _validate_path(RUNNER, package, "authoritative runner", kind="file")
    candidate_manifest = _validate_path(CANDIDATE_MANIFEST, package, "candidate manifest", kind="file")
    target = _validate_path(PACKAGE_DIR / "candidate" / "target", package, "candidate target", kind="dir")
    # The target directory and executable are created by Cargo.  Validate the
    # candidate against the existing package ancestry so a fresh checkout is
    # admissible, while the lexical/resolved walk still rejects an existing
    # target symlink, non-directory, loop, or escape.
    candidate = _validate_path(CANDIDATE_PATH, package, "candidate executable", kind="file")
    return {"root": root, "package": package, "manifest": manifest, "runner": runner, "candidate_manifest": candidate_manifest, "target": target, "candidate": candidate}


def _create_attempt(path: Path) -> None:
    try:
        path.mkdir(parents=True, exist_ok=False)
    except FileExistsError as error:
        raise WrapperError(f"attempt path already exists; refusing overwrite: {path}") from error
    except OSError as error:
        raise WrapperError(f"cannot create attempt path: {error}") from error


def _environment_allowlist(env: Mapping[str, str]) -> dict[str, str | None]:
    return {key: env.get(key) for key in ENV_ALLOWLIST}


def _build_environment(target_dir: Path | None = None) -> dict[str, str]:
    env = dict(os.environ)
    env["CARGO_BUILD_TARGET"] = CANDIDATE_TARGET
    env["CARGO_TARGET_DIR"] = str((target_dir or (PACKAGE_DIR / "candidate" / "target")).resolve())
    return env


def _validation_commands() -> list[list[str]]:
    return [
        [sys.executable, "-m", "unittest", "discover", "-s", str(SCRIPT_DIR), "-p", "test*.py"],
        [sys.executable, "-m", "py_compile", *(str(SCRIPT_DIR / name) for name in ("run_adapter.py", "runner_common.py", "runner_oracle.py", "runner_schema.py", "runner_transport.py"))],
        ["cargo", "test", "--manifest-path", str(CANDIDATE_MANIFEST.resolve()), "--target", CANDIDATE_TARGET, "--locked", "--offline"],
    ]


def _build_command() -> list[str]:
    return ["cargo", "build", "--manifest-path", str(CANDIDATE_MANIFEST.resolve()), "--target", CANDIDATE_TARGET, "--locked", "--offline"]


def _runner_command(result_path: Path) -> list[str]:
    return [
        sys.executable,
        str(RUNNER.resolve()),
        "--manifest",
        str(MANIFEST.resolve()),
        "--output",
        str(result_path.resolve()),
        "--",
        str(CANDIDATE_PATH.resolve()),
    ]


def _run_validation(env: Mapping[str, str]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index, argv in enumerate(_validation_commands()):
        result = _run_command(argv, cwd=REPOSITORY_ROOT, env=env)
        records.append({"stage": ("runner-unittest", "runner-py-compile", "candidate-cargo-test")[index], **result.as_receipt()})
        if result.exit_code != 0 or result.timed_out or result.output_bound_exceeded:
            break
    return records


def _run_version_observations(env: Mapping[str, str]) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    for argv in (("rustc", "-Vv"), ("cargo", "-V")):
        result = _run_command(argv, cwd=REPOSITORY_ROOT, env=env, timeout=OBSERVATION_DEADLINE_SECONDS, output_cap=MAX_ERROR_TEXT)
        observations.append({"stage": argv[0], **result.as_receipt()})
    return observations


def _result_cases(result: Mapping[str, Any]) -> list[dict[str, Any]]:
    corpora = result.get("corpora")
    if not isinstance(corpora, list):
        raise WrapperError("result corpora must be a list")
    cases: list[dict[str, Any]] = []
    for role in ROLES:
        entries = [value for value in corpora if isinstance(value, dict) and value.get("role") == role]
        if len(entries) != 1:
            raise WrapperError(f"result must contain exactly one {role} corpus")
        entry = entries[0]
        role_cases = entry.get("cases")
        if not isinstance(role_cases, list) or entry.get("processed_case_count") != len(role_cases) or entry.get("planned_case_count") != len(role_cases):
            raise WrapperError(f"{role} processed/planned case counts are inconsistent")
        for case in role_cases:
            if not isinstance(case, dict) or not isinstance(case.get("case_id"), str) or case.get("classification") not in CASE_CLASSIFICATIONS:
                raise WrapperError(f"invalid {role} case record")
        cases.extend(role_cases)
    if len(cases) != 49 or len({case["case_id"] for case in cases}) != 49:
        raise WrapperError("result must contain exactly 49 unique cases")
    return cases


def validate_result(
    result_path: Path,
    *,
    manifest_metadata: Mapping[str, Any],
    candidate_path: Path,
    candidate_sha256: str,
    source: Mapping[str, Any],
    runner_exit_code: int | None = None,
) -> dict[str, Any]:
    """Validate a completed runner result entirely offline; never invoke a runner."""

    result_sha256 = _file_sha256(result_path)
    try:
        with result_path.open("rb") as stream:
            raw = stream.read(MAX_RESULT_BYTES + 1)
    except OSError as error:
        raise WrapperError(f"cannot read result: {error}") from error
    if len(raw) > MAX_RESULT_BYTES:
        raise WrapperError(f"result exceeds {MAX_RESULT_BYTES}-byte cap")
    if hashlib.sha256(raw).hexdigest() != result_sha256:
        raise WrapperError("result changed while being read")
    candidate_observed_sha256 = _file_sha256(candidate_path, cap=MAX_ARTIFACT_BYTES)
    if candidate_observed_sha256 != candidate_sha256:
        raise WrapperError("candidate executable changed during offline validation")
    result = _strict_json(raw, cap=MAX_RESULT_BYTES)
    if not isinstance(result, dict):
        raise WrapperError("result root must be an object")
    required = {"schema", "experiment_id", "evaluation_binding", "profile_binding", "technology_result", "run_status", "evidence_status", "protocol_revision", "execution", "manifest", "candidate", "corpora", "relations", "summary", "relation_summary", "runner", "result_identity"}
    if not required <= set(result):
        raise WrapperError("result is missing required fields")
    if result.get("schema") != RESULT_SCHEMA or result.get("experiment_id") != "EXP-0002":
        raise WrapperError("result schema/experiment identity differs")
    if result.get("evaluation_binding") != EVALUATION_BINDING:
        raise WrapperError("result evaluation binding differs")
    if result.get("profile_binding") is not None or result.get("technology_result") != TECHNOLOGY_RESULT:
        raise WrapperError("result must remain profile-null and technology-result none")
    if result.get("run_status") != "complete" or result.get("evidence_status") not in {"passed", "failed", "inconclusive"}:
        raise WrapperError("result is not a completed passed/failed/inconclusive evidence result")
    if runner_exit_code is not None:
        expected_exit = 0 if result["evidence_status"] == "passed" else 2
        if runner_exit_code != expected_exit:
            raise WrapperError("runner exit code does not match completed evidence status")
    if not source.get("clean") or not source.get("untracked_covered"):
        raise WrapperError("source C was not clean or fully covered before execution")
    if result.get("execution") != {
        "candidate_processes": 1,
        "persistent_process": True,
        "corpus_sequence": list(ROLES),
        "held_out_role": "non-tuning-not-blind-or-process-isolated",
        "environment_observations": "workload-position-conditioned",
    }:
        raise WrapperError("result execution topology differs")

    expected_manifest = {
        "sha256": manifest_metadata["manifest_sha256"],
        "corpora": manifest_metadata["corpora"],
        "oracle_bound": manifest_metadata["oracle_bound"],
    }
    if result.get("manifest") != expected_manifest:
        raise WrapperError("result manifest identity/count/order differs")
    result_cases = _result_cases(result)
    expected_case_ids = [case_id for corpus in manifest_metadata["corpora"] for case_id in corpus["case_ids"]]
    if [case["case_id"] for case in result_cases] != expected_case_ids:
        raise WrapperError("result case identity/order differs from manifest")
    relation_values = result.get("relations")
    expected_relations = list(manifest_metadata["relations"].values())
    if not isinstance(relation_values, list) or len(relation_values) != 26:
        raise WrapperError("result must contain exactly 26 relation records")
    if [value.get("id") if isinstance(value, dict) else None for value in relation_values] != [value["id"] for value in expected_relations]:
        raise WrapperError("result relation order/identity differs")
    for value, expected in zip(relation_values, expected_relations):
        if not isinstance(value, dict) or value.get("meaning") != expected["meaning"] or value.get("case_ids") != expected["cases"] or value.get("classification") not in CASE_CLASSIFICATIONS:
            raise WrapperError(f"result relation metadata differs for {expected['id']}")

    summary = result.get("summary")
    relation_summary = result.get("relation_summary")
    case_counts = {classification: 0 for classification in CASE_CLASSIFICATIONS}
    for case in result_cases:
        case_counts[case["classification"]] += 1
    relation_counts = {classification: 0 for classification in CASE_CLASSIFICATIONS}
    for relation in relation_values:
        relation_counts[relation["classification"]] += 1
    if summary != case_counts or relation_summary != relation_counts:
        raise WrapperError("result summaries do not match actual case/relation classifications")
    for name, value, total in (("summary", summary, 49), ("relation_summary", relation_summary, 26)):
        if not isinstance(value, dict) or set(value) != set(CASE_CLASSIFICATIONS) or any(isinstance(count, bool) or not isinstance(count, int) or count < 0 for count in value.values()) or sum(value.values()) != total:
            raise WrapperError(f"result {name} vocabulary/counts are invalid")
    if case_counts["incomplete"] or relation_counts["incomplete"]:
        derived_evidence_status = "incomplete"
    elif case_counts["fail"] or relation_counts["fail"]:
        derived_evidence_status = "failed"
    elif case_counts["inconclusive"] or case_counts["unsupported"] or relation_counts["inconclusive"] or relation_counts["unsupported"]:
        derived_evidence_status = "inconclusive"
    else:
        derived_evidence_status = "passed"
    if result["evidence_status"] != derived_evidence_status:
        raise WrapperError("result evidence status contradicts case/relation classifications")

    candidate = result.get("candidate")
    identity = result.get("result_identity")
    runner = result.get("runner")
    if not isinstance(candidate, dict) or not isinstance(identity, dict) or not isinstance(runner, dict):
        raise WrapperError("result candidate/runner/result_identity objects are required")
    if candidate.get("executable") != str(candidate_path.resolve()) or candidate.get("executable_sha256") != candidate_sha256:
        raise WrapperError("result candidate executable hash/path does not match built candidate")
    if candidate.get("execution_command", [None])[0] != str(candidate_path.resolve()):
        raise WrapperError("result candidate execution command does not match built candidate")
    if runner.get("evaluation_binding") != EVALUATION_BINDING or identity.get("evaluation_binding") != EVALUATION_BINDING:
        raise WrapperError("runner/result identity binding differs")
    if identity.get("schema") != "ck.exp-0002.result-identity-1" or identity.get("manifest_sha256") != manifest_metadata["manifest_sha256"]:
        raise WrapperError("result identity schema/manifest differs")
    if identity.get("runner_bundle_sha256") != runner.get("bundle_sha256"):
        raise WrapperError("runner bundle identity differs")
    artifacts = candidate.get("command_artifacts")
    identity_artifacts = identity.get("candidate_command_artifacts")
    if not isinstance(artifacts, list) or identity_artifacts != artifacts:
        raise WrapperError("candidate command-artifact identity differs")
    executable_artifact = next((item for item in artifacts if isinstance(item, dict) and item.get("argument_index") == 0), None)
    if not isinstance(executable_artifact, dict) or executable_artifact.get("sha256") != candidate_sha256:
        raise WrapperError("candidate executable artifact hash is not cross-checked")
    if identity.get("candidate_execution_command") != candidate.get("execution_command") or identity.get("candidate_command") != candidate.get("command"):
        raise WrapperError("candidate command identity differs")
    result_identity = identity.get("identity")
    if not isinstance(result_identity, dict) or result_identity.get("stability") != "verified":
        raise WrapperError("candidate/runner identity stability was not verified")
    pre_artifacts = result_identity.get("pre_run", {}).get("candidate_artifacts") if isinstance(result_identity.get("pre_run"), dict) else None
    post_artifacts = result_identity.get("post_run", {}).get("candidate_artifacts") if isinstance(result_identity.get("post_run"), dict) else None
    if not isinstance(pre_artifacts, list) or not isinstance(post_artifacts, list) or not pre_artifacts or not post_artifacts:
        raise WrapperError("candidate pre/post identity evidence is missing")
    if pre_artifacts[0].get("sha256") != candidate_sha256 or post_artifacts[0].get("sha256") != candidate_sha256:
        raise WrapperError("candidate pre/post identity hash differs")
    build_identity = candidate.get("build_identity")
    candidate_source = build_identity.get("source") if isinstance(build_identity, dict) else None
    if not isinstance(candidate_source, dict) or candidate_source.get("git_commit") != source["commit"]:
        raise WrapperError("result candidate source commit differs from source C")
    if identity.get("profile_binding") is not None or identity.get("technology_result") != TECHNOLOGY_RESULT:
        raise WrapperError("result identity profile/technology fields differ")
    if runner.get("budgets") != identity.get("configured_budgets"):
        raise WrapperError("runner configured budgets do not match result identity")
    if result.get("protocol_revision") != "ck.r3.numeric-candidate-request-1":
        raise WrapperError("result protocol revision differs")
    return {
        "status": "verified",
        "sha256": result_sha256,
        "bytes": len(raw),
        "cases": 49,
        "relations": 26,
        "evidence_status": result["evidence_status"],
        "crosschecks": {
            "manifest_and_corpus_identity": "verified",
            "binding": "verified",
            "case_count": 49,
            "relation_count": 26,
            "runner_result_identity": "verified",
            "identity_stability": "verified",
            "source_commit": source["commit"],
            "source_pre_run_clean": bool(source.get("clean")),
            "candidate_executable_hash": "verified",
            "runner_exit_evidence": "verified" if runner_exit_code is not None else "not-supplied",
            "profile_binding": None,
            "technology_result": TECHNOLOGY_RESULT,
        },
    }


def _write_receipt(path: Path, receipt: Mapping[str, Any]) -> None:
    payload = json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n"
    if len(payload) > MAX_RECEIPT_BYTES:
        raise WrapperError(f"receipt exceeds {MAX_RECEIPT_BYTES}-byte cap")
    try:
        fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.partial-", dir=path.parent)
    except OSError as error:
        raise WrapperError(f"cannot create receipt temporary file: {error}") from error
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError as error:
            raise WrapperError("receipt already exists; refusing overwrite") from error
        try:
            directory_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        except OSError:
            directory_fd = None
        if directory_fd is not None:
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        temporary.unlink()
    except Exception:
        # Keep the uniquely named non-final artifact for diagnosis.  The
        # final receipt path is only created by the exclusive hard-link.
        raise


def _failure(stage: str, message: str) -> dict[str, str]:
    bounded = message[:MAX_ERROR_TEXT]
    return {"stage": stage, "text": bounded, "sha256": hashlib.sha256(bounded.encode("utf-8")).hexdigest()}


def _require_source_checkpoint(snapshot: Mapping[str, Any], commit: str, stage: str) -> None:
    if snapshot.get("commit") != commit:
        raise WrapperError(f"source commit changed after {stage}")
    if not snapshot.get("clean") or not snapshot.get("untracked_covered"):
        raise WrapperError(f"source tree is not clean or fully covered after {stage}")


def plan() -> dict[str, Any]:
    return {
        "schema": "ck.exp-0002.phase1-run-plan-1",
        "experiment_id": "EXP-0002",
        "evaluation_binding": EVALUATION_BINDING,
        "mode": "preflight-only",
        "authoritative_runner_invocations": 0,
        "attempt_created": False,
        "acknowledgement": "required for execution",
        "attempt_id": "required and must match attempt-[0-9]{3,}",
        "source_clean_gate": "tracked, staged, and non-ignored untracked files must all be clean",
        "target": CANDIDATE_TARGET,
        "profile": "cargo default dev/debug",
        "validation_argv": _validation_commands(),
        "build_argv": _build_command(),
        "runner_argv_shape": "run_adapter.py --manifest <absolute frozen manifest> --output <absolute new result> -- <absolute candidate>",
        "result_integrity": "offline only; no corpus rerun",
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt-id", help="new attempt ID, for example attempt-001")
    parser.add_argument("--acknowledge", "--acknowledgement", dest="acknowledge", help=f"required exact execution acknowledgement: {ACKNOWLEDGEMENT}")
    parser.add_argument("--execute", action="store_true", help="required alongside --acknowledge to execute the frozen corpus")
    parser.add_argument("--preflight-only", action="store_true", help="print a plan; never create an attempt or invoke run_adapter.py")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.preflight_only:
        print(json.dumps(plan(), sort_keys=True, indent=2))
        return 0
    if not args.execute or args.acknowledge != ACKNOWLEDGEMENT:
        print(f"refusing execution: both --execute and --acknowledge {ACKNOWLEDGEMENT} are required", file=sys.stderr)
        return 2
    if not args.attempt_id:
        print("refusing execution: --attempt-id is required", file=sys.stderr)
        return 2
    try:
        attempt_id = validate_attempt_id(args.attempt_id)
        fixed_paths = _validate_fixed_paths(REPOSITORY_ROOT)
        source = source_snapshot(fixed_paths["root"])
        _require_source_checkpoint(source, source["commit"], "initial source check")
        commit = source["commit"]
        destination = attempt_path(fixed_paths["root"], commit, attempt_id)
        _validate_path(destination, fixed_paths["root"], "attempt", kind="dir")
        result_path = destination / "result.json"
        receipt_path = destination / "receipt.json"
        env = _build_environment(fixed_paths["target"])
        receipt: dict[str, Any] = {
            "schema": RECEIPT_SCHEMA,
            "experiment_id": "EXP-0002",
            "evaluation_binding": EVALUATION_BINDING,
            "attempt": {"id": attempt_id, "path": str(destination), "source_commit": commit},
            "source": source,
            "paths": {key: str(value) for key, value in fixed_paths.items()},
            "profile": "cargo default dev/debug",
            "target": CANDIDATE_TARGET,
            "environment": {"allowlist": _environment_allowlist(env)},
            "source_checkpoints": {"post_validation": None, "post_build": None},
            "validation": {"commands": [], "complete": False},
            "build": {"command": _build_command(), "exit_code": None, "observations": []},
            "runner": {"command": None, "invocations": 0, "exit_code": None},
            "executable": {"path": str(fixed_paths["candidate"]), "sha256_pre": None, "sha256_post": None, "sha256_after_run": None},
            "result": {"path": str(result_path), "sha256": None, "integrity": "not-checked", "crosschecks": {}},
            "failure": None,
        }
        _create_attempt(destination)
    except (WrapperError, OSError) as error:
        print(f"EXP-0002 phase-one wrapper error: {error}", file=sys.stderr)
        return 2
    outcome = 2
    failure_stage = "validation"
    try:
        try:
            _manifest, _corpora, metadata = load_manifest(MANIFEST.resolve())
        except Exception as error:  # schema loader uses several bounded validation exceptions
            raise WrapperError(f"manifest/corpus preflight failed: {error}") from error
        receipt["manifest"] = {"path": str(MANIFEST.resolve()), "sha256": metadata["manifest_sha256"], "evaluation_binding": metadata["evaluation_binding"]}

        validation_records = _run_validation(env)
        receipt["validation"] = {"commands": validation_records, "complete": bool(validation_records) and len(validation_records) == 3 and all(item["exit_code"] == 0 for item in validation_records)}
        if not receipt["validation"]["complete"]:
            raise WrapperError("synthetic validation failed")
        current_source = source_snapshot(fixed_paths["root"])
        receipt["source_checkpoints"]["post_validation"] = current_source
        _require_source_checkpoint(current_source, commit, "validation")

        failure_stage = "build"
        receipt["build"]["observations"] = _run_version_observations(env)
        pre_hash = _file_sha256(CANDIDATE_PATH, cap=MAX_ARTIFACT_BYTES) if CANDIDATE_PATH.exists() else None
        receipt["executable"]["sha256_pre"] = pre_hash
        build = _run_command(_build_command(), cwd=REPOSITORY_ROOT, env=env)
        receipt["build"].update(build.as_receipt())
        if build.exit_code != 0 or build.timed_out or build.output_bound_exceeded:
            raise WrapperError("candidate build failed")
        post_hash = _file_sha256(CANDIDATE_PATH, cap=MAX_ARTIFACT_BYTES)
        receipt["executable"]["sha256_post"] = post_hash
        current_source = source_snapshot(fixed_paths["root"])
        receipt["source_checkpoints"]["post_build"] = current_source
        _require_source_checkpoint(current_source, commit, "candidate build")

        failure_stage = "runner"
        runner_argv = _runner_command(result_path)
        receipt["runner"].update({"command": runner_argv, "invocations": 1})
        runner = _run_command(runner_argv, cwd=REPOSITORY_ROOT, env=env)
        receipt["runner"].update(runner.as_receipt())
        if runner.exit_code is None:
            raise WrapperError("authoritative runner exit code is unavailable")
        after_run_hash = _file_sha256(CANDIDATE_PATH, cap=MAX_ARTIFACT_BYTES)
        receipt["executable"]["sha256_after_run"] = after_run_hash
        if after_run_hash != post_hash:
            raise WrapperError("candidate executable changed during authoritative run")
        # A result, including failed/inconclusive evidence, is preserved for
        # offline checking even when run_adapter returns its normal status 2.
        if not result_path.exists():
            raise WrapperError("authoritative runner produced no result")
        failure_stage = "integrity"
        integrity = validate_result(result_path, manifest_metadata=metadata, candidate_path=CANDIDATE_PATH, candidate_sha256=post_hash, source=source, runner_exit_code=runner.exit_code)
        receipt["result"].update(integrity)
        receipt["result"]["integrity"] = "verified"
        receipt["outcome"] = "completed-evidence"
        outcome = 0
    except Exception as error:
        receipt["failure"] = _failure(failure_stage, str(error))
        outcome = 2
    finally:
        try:
            _write_receipt(receipt_path, receipt)
        except Exception as error:
            print(f"EXP-0002 phase-one wrapper error writing receipt: {error}", file=sys.stderr)
            outcome = 2
    if receipt.get("failure"):
        print(f"EXP-0002 phase-one wrapper failed at {receipt['failure']['stage']}: {receipt['failure']['text']}", file=sys.stderr)
    return outcome


if __name__ == "__main__":
    raise SystemExit(main())

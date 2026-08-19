#!/usr/bin/env python3
"""Check the immutable candidate source/build closure for EXP-0002 phase 3.

This is deliberately a check-only tool.  It reads the base Git tree and the
working tree, and never writes either one.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import posixpath
import re
import stat
import struct
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REPO = Path(__file__).resolve().parents[4]
GIT_EXECUTABLE = "/usr/bin/git"
# Candidate closure reads must not inherit locale, Git configuration, home or
# optional lock behaviour from the caller.  Keep this environment exact and
# closed for both standalone and freeze-loaded use.
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
BASE_COMMIT = "f4125342211a1d1436ae48b685ec2342700f39c4"
CANDIDATE_DIR = "experiments/EXP-0002-numeric-frame-profile/phase2-authored-conflict/candidate"
CORE_DIR = "crates/creature-kernel-core"
BASE_PATH_SET_PREFIX = b"ck.phase3-candidate-source-build-path-set.v1\0"
CONTENT_PREFIX = b"ck.phase3-candidate-source-build-content.v1\0"
EXPECTED_COUNT = 47
EXPECTED_BYTES = 1_494_337
EXPECTED_PATH_SHA256 = "10605701d02f117ff7ef2756004fbf53a475eb92fbc0616e139f919d7a8480dc"
EXPECTED_CONTENT_SHA256 = "21825e78c3286cf73d135f44be99eaea5214ce36b5fed6271dce096d364468e2"
SCHEMA_PATH = "spec/body-document/schema/ck-body-document-v1.schema.json"


class CheckError(RuntimeError):
    """A fail-closed prebinding check failure."""


@dataclass(frozen=True)
class Entry:
    path: str
    mode: int
    content: bytes


@dataclass(frozen=True)
class Identity:
    count: int
    total_bytes: int
    path_sha256: str
    content_sha256: str


def parse_git_mode(mode_text: str) -> int:
    """Parse Git's six-digit textual mode as octal, never as decimal."""
    if len(mode_text) != 6 or not re.fullmatch(r"[0-7]{6}", mode_text):
        raise CheckError(f"invalid Git mode {mode_text!r}")
    mode = int(mode_text, 8)
    if not stat.S_ISREG(mode):
        raise CheckError(f"Git path is not a regular file mode: {mode_text}")
    return mode


def normalize_repo_path(path: str) -> str:
    """Normalize a repository-relative path and reject unsafe components."""
    if not path or path.startswith("/") or path.startswith("./"):
        raise CheckError(f"invalid repository-relative path: {path!r}")
    parts = path.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise CheckError(f"invalid repository-relative path: {path!r}")
    return "/".join(parts)


def _git(repo: Path, *args: str) -> bytes:
    result = subprocess.run(
        [GIT_EXECUTABLE, "-C", str(repo), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=dict(GIT_ENV),
    )
    if result.returncode:
        detail = result.stderr.decode("utf-8", "replace").strip()
        raise CheckError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout


def _parse_ls_tree(raw: bytes) -> list[tuple[str, str, str]]:
    records: list[tuple[str, str, str]] = []
    for record in raw.split(b"\0"):
        if not record:
            continue
        try:
            meta, path_raw = record.split(b"\t", 1)
            mode, kind, object_id = meta.decode("ascii").split(" ")
            path = path_raw.decode("utf-8")
        except (UnicodeDecodeError, ValueError) as exc:
            raise CheckError("malformed Git tree record") from exc
        records.append((mode, kind, normalize_repo_path(path)))
    return records


def _tree_entries(repo: Path, commit: str, selectors: Iterable[str] | None = None) -> dict[str, Entry]:
    args = ["ls-tree", "-r", "-z", commit]
    if selectors:
        args += ["--", *selectors]
    records = _parse_ls_tree(_git(repo, *args))
    entries: dict[str, Entry] = {}
    for mode_text, kind, path in records:
        if path in entries:
            raise CheckError(f"duplicate Git path: {path}")
        mode = parse_git_mode(mode_text) if kind == "blob" else 0
        if kind != "blob":
            raise CheckError(f"Git path is not a regular blob: {path}")
        content = _git(repo, "show", f"{commit}:{path}")
        entries[path] = Entry(path, mode, content)
    return entries


def _all_blob_entries(repo: Path, commit: str) -> tuple[dict[str, Entry], set[str]]:
    """Read all blobs while retaining non-blob names for fail-closed targets."""
    records = _parse_ls_tree(_git(repo, "ls-tree", "-r", "-z", commit))
    entries: dict[str, Entry] = {}
    all_paths: set[str] = set()
    for mode_text, kind, path in records:
        if path in all_paths:
            raise CheckError(f"duplicate Git path: {path}")
        all_paths.add(path)
        if kind != "blob" or not mode_text.startswith("100"):
            continue
        mode = parse_git_mode(mode_text)
        entries[path] = Entry(path, mode, _git(repo, "show", f"{commit}:{path}"))
    return entries, all_paths


def _base_seed_entries(repo: Path, commit: str) -> dict[str, Entry]:
    selectors = [CANDIDATE_DIR, CORE_DIR, "Cargo.toml", "rust-toolchain.toml"]
    return _tree_entries(repo, commit, selectors)


def _matching_brace(text: str, opening: int) -> int | None:
    depth = 0
    i = opening
    while i < len(text):
        if text.startswith("//", i):
            end = text.find("\n", i + 2)
            i = len(text) if end < 0 else end
            continue
        if text.startswith("/*", i):
            end = text.find("*/", i + 2)
            if end < 0:
                return None
            i = end + 2
            continue
        skipped = _skip_rust_literal(text, i)
        if skipped is not None:
            i = skipped
            continue
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return None


def _skip_rust_literal(text: str, start: int) -> int | None:
    """Return the end of a Rust string/char/raw-string literal at *start*."""
    quote_at = start
    if text[start] in ('b', 'r'):
        quote_at = start + 1
        if text.startswith("br", start) or text.startswith("rb", start):
            quote_at = start + 2
        if quote_at < len(text) and text[quote_at] == "r":
            quote_at += 1
        if quote_at < len(text) and text[quote_at] == "#":
            while quote_at < len(text) and text[quote_at] == "#":
                quote_at += 1
        if quote_at >= len(text) or text[quote_at] != '"':
            return None
    elif text[start] not in ('"', "'"):
        return None
    if text[quote_at] == '"' and quote_at > start and text[start:quote_at].rstrip("#") in ("r", "br", "rb"):
        hashes = len(text[start:quote_at]) - len(text[start:quote_at].rstrip("#"))
        terminator = '"' + ('#' * hashes)
        end = text.find(terminator, quote_at + 1)
        return None if end < 0 else end + len(terminator)
    quote = text[quote_at]
    i = quote_at + 1
    while i < len(text):
        if text[i] == "\\":
            i += 2
        elif text[i] == quote:
            return i + 1
        else:
            i += 1
    return None


def _mask_cfg_test_regions(text: str) -> str:
    """Mask cfg(test) items while preserving offsets for diagnostics/scanning."""
    mask = list(text)
    attr_re = re.compile(r"#\s*\[\s*cfg\s*\(\s*test\s*\)\s*\]")
    for match in attr_re.finditer(text):
        opening = text.find("{", match.end())
        semicolon = text.find(";", match.end())
        if opening < 0 or (semicolon >= 0 and semicolon < opening):
            end = len(text) if semicolon < 0 else semicolon + 1
        else:
            closing = _matching_brace(text, opening)
            if closing is None:
                raise CheckError("unterminated cfg(test) item")
            end = closing + 1
        for index in range(match.start(), end):
            if mask[index] != "\n":
                mask[index] = " "
    return "".join(mask)


def _matching_paren(text: str, opening: int) -> int | None:
    depth = 0
    i = opening
    while i < len(text):
        if text.startswith("//", i):
            end = text.find("\n", i + 2)
            i = len(text) if end < 0 else end
            continue
        if text.startswith("/*", i):
            end = text.find("*/", i + 2)
            if end < 0:
                return None
            i = end + 2
            continue
        skipped = _skip_rust_literal(text, i)
        if skipped is not None:
            i = skipped
            continue
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return None


def _decode_literal(expression: str) -> str:
    expression = re.sub(r"/\*.*?\*/|//[^\n]*", "", expression, flags=re.S)
    expression = expression.strip()
    if not re.fullmatch(r'"(?:[^"\\]|\\.)*"', expression, flags=re.S):
        raise CheckError(f"unsupported dynamic compile-time include expression: {expression!r}")
    # JSON's string escapes are the common Rust path-literal subset.  Reject
    # anything else instead of guessing at Rust-specific escapes.
    import json

    try:
        value = json.loads(expression)
    except (TypeError, ValueError) as exc:
        raise CheckError("invalid compile-time include string literal") from exc
    if not isinstance(value, str):
        raise CheckError("compile-time include is not a string literal")
    return value


def _include_references(source: str, source_path: str) -> set[tuple[str, str]]:
    active = _mask_cfg_test_regions(source)
    references: set[tuple[str, str]] = set()
    macro_re = re.compile(r"\b(include|include_str|include_bytes)\s*!\s*\(")
    for match in macro_re.finditer(active):
        opening = active.rfind("(", match.start(), match.end())
        closing = _matching_paren(active, opening)
        if closing is None:
            raise CheckError(f"unterminated compile-time include in {source_path}")
        literal = _decode_literal(active[opening + 1 : closing])
        if "\\" in literal or "\0" in literal:
            raise CheckError(f"invalid local include path in {source_path}")
        joined = posixpath.normpath(posixpath.join(posixpath.dirname(source_path), literal))
        try:
            target = normalize_repo_path(joined)
        except CheckError as exc:
            raise CheckError(f"compile-time include escapes repository: {source_path}: {literal!r}") from exc
        references.add((target, match.group(1)))
    return references


def _include_targets(source: str, source_path: str) -> set[str]:
    """Return validated literal include targets (test regions excluded)."""
    return {target for target, _ in _include_references(source, source_path)}


def _add_literal_include_targets(repo: Path, commit: str, entries: dict[str, Entry]) -> None:
    sources = [entry for entry in entries.values() if entry.path.endswith(".rs")]
    all_tree, all_paths = _all_blob_entries(repo, commit)
    queue = list(sources)
    visited: set[str] = set()
    while queue:
        entry = queue.pop()
        if entry.path in visited:
            continue
        visited.add(entry.path)
        try:
            source = entry.content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise CheckError(f"Rust source is not UTF-8: {entry.path}") from exc
        references = _include_references(source, entry.path)
        for target, macro in sorted(references, key=lambda item: item[0].encode("utf-8")):
            target_entry = all_tree.get(target)
            if target_entry is None:
                if target in all_paths:
                    raise CheckError(f"compile-time include target is not a regular file: {target}")
                raise CheckError(f"unbound compile-time include target: {target}")
            if macro == "include" and target not in visited:
                queue.append(target_entry)
            if target in entries:
                continue
            entries[target] = target_entry


def select_base_entries(repo: Path = REPO, commit: str = BASE_COMMIT) -> list[Entry]:
    entries = _base_seed_entries(repo, commit)
    _add_literal_include_targets(repo, commit, entries)
    ordered = sorted(entries.values(), key=lambda entry: entry.path.encode("utf-8"))
    if SCHEMA_PATH not in entries:
        raise CheckError(f"required body-document schema was not selected: {SCHEMA_PATH}")
    return ordered


def _stream(entries: list[Entry], with_content: bool) -> bytes:
    prefix = CONTENT_PREFIX if with_content else BASE_PATH_SET_PREFIX
    output = bytearray(prefix)
    for entry in entries:
        path = entry.path.encode("utf-8")
        output += struct.pack(">I", len(path)) + path + struct.pack(">I", entry.mode)
        if with_content:
            output += struct.pack(">Q", len(entry.content)) + entry.content
    return bytes(output)


def identity(entries: Iterable[Entry]) -> Identity:
    ordered = sorted(entries, key=lambda entry: entry.path.encode("utf-8"))
    paths = [entry.path for entry in ordered]
    if len(paths) != len(set(paths)):
        raise CheckError("duplicate closure path")
    total = sum(len(entry.content) for entry in ordered)
    return Identity(
        count=len(ordered),
        total_bytes=total,
        path_sha256=hashlib.sha256(_stream(ordered, False)).hexdigest(),
        content_sha256=hashlib.sha256(_stream(ordered, True)).hexdigest(),
    )


def _reject_new_build_inputs(repo: Path, commit: str) -> None:
    base_paths = set(_parse_ls_tree(_git(repo, "ls-tree", "-r", "-z", commit)))
    base_names = {path for _, _, path in base_paths}
    found = _new_build_inputs(repo, base_names)
    if found:
        raise CheckError("new Cargo build input present: " + ", ".join(found))


def _relevant_build_input_paths(repo: Path) -> list[str]:
    """Find inputs Cargo can consume for the standalone candidate invocation.

    The assumed context is an invocation of the candidate manifest from the
    repository root (or with the candidate directory as its working
    directory).  Cargo may use build.rs beside the candidate or its core path
    dependency, and config/config.toml in .cargo directories from the
    candidate directory through the repository root.  Exact Gate B cwd
    selection is intentionally outside this check.
    """
    candidate = repo / CANDIDATE_DIR
    core = repo / CORE_DIR
    paths: list[Path] = [candidate / "build.rs", core / "build.rs"]
    current = candidate
    while True:
        cargo_dir = current / ".cargo"
        try:
            cargo_info = os.lstat(cargo_dir)
        except FileNotFoundError:
            cargo_info = None
        if cargo_info is not None:
            if stat.S_ISLNK(cargo_info.st_mode) or not stat.S_ISDIR(cargo_info.st_mode):
                paths.append(cargo_dir)
            else:
                paths.extend(cargo_dir / name for name in ("config", "config.toml"))
        if current == repo:
            break
        if repo not in current.parents:
            break
        current = current.parent
    return sorted(path.relative_to(repo).as_posix() for path in paths if path.exists() or path.is_symlink())


def _new_build_inputs(repo: Path, base_names: set[str]) -> list[str]:
    """Find relevant Cargo inputs absent from base Git; ignore unrelated packages."""
    return [path for path in _relevant_build_input_paths(repo) if path not in base_names]


def _safe_current_entry(repo: Path, entry: Entry) -> Entry:
    path = repo.joinpath(*entry.path.split("/"))
    current = repo
    for component in entry.path.split("/"):
        current = current / component
        try:
            info = os.lstat(current)
        except FileNotFoundError as exc:
            raise CheckError(f"missing closure path: {entry.path}") from exc
        if stat.S_ISLNK(info.st_mode):
            raise CheckError(f"symlink in closure path: {entry.path}")
    info = os.lstat(path)
    if not stat.S_ISREG(info.st_mode):
        raise CheckError(f"non-regular closure path: {entry.path}")
    current_mode = stat.S_IFREG | stat.S_IMODE(info.st_mode)
    if current_mode != entry.mode:
        raise CheckError(f"current mode mismatch for {entry.path}: expected {entry.mode:o}, got {current_mode:o}")
    try:
        content = path.read_bytes()
    except OSError as exc:
        raise CheckError(f"cannot read closure path: {entry.path}") from exc
    if content != entry.content:
        raise CheckError(f"current content mismatch for {entry.path}")
    return Entry(entry.path, current_mode, content)


def check(repo: Path = REPO, commit: str = BASE_COMMIT) -> tuple[Identity, Identity]:
    _reject_new_build_inputs(repo, commit)
    base_entries = select_base_entries(repo, commit)
    base_identity = identity(base_entries)
    expected = Identity(EXPECTED_COUNT, EXPECTED_BYTES, EXPECTED_PATH_SHA256, EXPECTED_CONTENT_SHA256)
    if base_identity != expected:
        raise CheckError(f"base identity mismatch: {base_identity}")
    current_entries = [_safe_current_entry(repo, entry) for entry in base_entries]
    current_identity = identity(current_entries)
    if current_identity != expected:
        raise CheckError(f"current identity mismatch: {current_identity}")
    return base_identity, current_identity


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="check the prebound EXP-0002 candidate closure")
    parser.add_argument("--repo", type=Path, default=REPO)
    parser.add_argument("--commit", default=BASE_COMMIT)
    args = parser.parse_args(argv)
    try:
        base, current = check(args.repo.resolve(), args.commit)
    except CheckError as exc:
        print(f"CANDIDATE PREBINDING CHECK FAILED: {exc}")
        return 1
    print(f"CANDIDATE PREBINDING CHECK OK: {base.count} files, {base.total_bytes} bytes, base/current identities match")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

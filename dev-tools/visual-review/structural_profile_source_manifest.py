"""Validate the active exact-five generated structural source bundle.

This is a small, importable consumer boundary for the active regional gallery.
It executes the active source generator only from one verified immutable byte
snapshot and keeps the historical gallery renderers and publishers out of the
validation path.
"""

from __future__ import annotations

import builtins
import hashlib
import json
import os
import re
import stat
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import ModuleType
from typing import Any, NoReturn


EXPERIMENT_ROOT = Path(__file__).resolve().parents[2] / "experiments" / "current-form-surface-preview"
REPOSITORY_ROOT = EXPERIMENT_ROOT.parents[1]


SOURCE_MANIFEST_FORMAT = "creature-kernel.disposable-structural-profile-source-manifest.v1"
PROFILE_COUNT = 5
MAX_MANIFEST_BYTES = 1024 * 1024
MAX_SOURCE_BYTES = 65_536
MAX_UPSTREAM_BYTES = 1024 * 1024
MAX_GENERATOR_BYTES = 1024 * 1024
MAX_IMPLEMENTATION_BYTES = 1024 * 1024
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PROFILE_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")
READ_CHUNK = 64 * 1024
VALIDATOR_IMPLEMENTATION_ID = (
    "structural_profile_source_manifest.validate_structural_profile_source_manifest"
)


class StructuralProfileSourceManifestError(ValueError):
    """A bounded, fail-closed source-manifest validation failure."""


_GENERATOR_PUBLISH_MODULE = "structural_atomic_publish"


class _UnavailableGeneratorDependency(ModuleType):
    """An explicitly unavailable publisher dependency for source-only execution."""

    def __getattr__(self, name: str) -> NoReturn:
        raise RuntimeError(
            f"generator snapshot attempted to use unavailable {_GENERATOR_PUBLISH_MODULE}.{name}"
        )


# A descriptive alias keeps the public exception easy to discover for callers
# that think in terms of the manifest rather than the experiment name.
SourceManifestValidationError = StructuralProfileSourceManifestError


@dataclass(frozen=True)
class SourceProvenance:
    """The source identity/provenance retained by a generated document."""

    document: str
    namespace: str
    dependencies: Any


@dataclass(frozen=True)
class GeneratedSourceRecord:
    """One ordered generated source and its independently checked identity."""

    id: str
    path: Path
    document: str
    namespace: str
    sha256: str
    bytes: int
    tail_signature: tuple[int, int, int, int, int]
    provenance: SourceProvenance

    @property
    def profile_id(self) -> str:
        return self.id

    @property
    def source_document(self) -> str:
        return self.document


@dataclass(frozen=True)
class ManifestLineage:
    """Content identity and source bindings carried by the manifest."""

    path: Path
    sha256: str
    bytes: int
    format: str
    candidate_format: str
    candidate_sha256: str
    base_source_sha256: str
    base_document: str
    base_namespace: str
    profile_ids: tuple[str, ...]


@dataclass(frozen=True)
class GeneratorLineage:
    """The active generator contract and its checked-in input identities."""

    path: Path
    sha256: str
    bytes: int
    mode: str
    format: str
    source_document_suffix: str
    profile_ids: tuple[str, ...]
    candidate_path: Path
    base_source_path: Path
    candidate_sha256: str
    base_source_sha256: str

    @property
    def generation_mode(self) -> str:
        return self.mode

    @property
    def candidate_format(self) -> str:
        return self.format


@dataclass(frozen=True)
class _GeneratorSnapshot:
    """The exact generator bytes that were compiled and executed."""

    module: ModuleType
    path: Path
    bytes: bytes


@dataclass(frozen=True)
class _ImplementationSourceSnapshot:
    """The immutable validator source bytes from which this module executes."""

    path: Path
    source_bytes: bytes
    sha256: str

    @property
    def identity(self) -> dict[str, Any]:
        return {
            "id": VALIDATOR_IMPLEMENTATION_ID,
            "bytes": len(self.source_bytes),
            "sha256": self.sha256,
        }


@dataclass(frozen=True)
class _SourceDirectorySnapshot:
    """One opened source-directory identity and its exact entry names."""

    path: Path
    device: int
    inode: int
    entries: tuple[str, ...]

    @property
    def identity(self) -> tuple[int, int]:
        return self.device, self.inode


@dataclass(frozen=True)
class SourceManifestValidationResult:
    """Immutable validation result for the exact ordered source bundle."""

    manifest: ManifestLineage
    generator: GeneratorLineage
    profile_ids: tuple[str, ...]
    sources: tuple[GeneratedSourceRecord, ...]

    @property
    def manifest_path(self) -> Path:
        return self.manifest.path

    @property
    def manifest_sha256(self) -> str:
        return self.manifest.sha256

    @property
    def manifest_bytes(self) -> int:
        return self.manifest.bytes

    @property
    def source_documents(self) -> tuple[GeneratedSourceRecord, ...]:
        return self.sources

    @property
    def generator_lineage(self) -> GeneratorLineage:
        return self.generator


def _fail(message: str) -> NoReturn:
    raise StructuralProfileSourceManifestError(message)


def _absolute_lexical(value: os.PathLike[str] | str, where: str) -> Path:
    try:
        raw = os.fspath(value)
        path = Path(raw)
        return path if path.is_absolute() else Path.cwd() / path
    except (OSError, TypeError, ValueError) as exc:
        _fail(f"{where} is not a usable path: {exc}")


def _reject_symlink_components(path: Path, where: str) -> None:
    """Reject symlinks in a lexical path without resolving through them."""

    current = Path(path.anchor)
    for component in path.parts[1:]:
        if component == ".":
            continue
        if component == "..":
            current = current.parent
            continue
        current /= component
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            continue
        except OSError as exc:
            _fail(f"could not inspect {where}: {exc}")
        if stat.S_ISLNK(mode):
            _fail(f"{where} may not use symlinks: {current}")


def _read_regular_file(path: Path, maximum: int, where: str) -> tuple[Path, bytes]:
    """Read one stable regular file with a bounded, no-follow descriptor."""

    absolute = _absolute_lexical(path, where)
    _reject_symlink_components(absolute, where)
    try:
        path_info = absolute.lstat()
    except OSError as exc:
        _fail(f"{where} cannot be inspected safely: {exc}")
    if stat.S_ISLNK(path_info.st_mode) or not stat.S_ISREG(path_info.st_mode):
        _fail(f"{where} must be a regular file")
    if path_info.st_size > maximum:
        _fail(f"{where} exceeds the bounded size of {maximum} bytes")

    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd: int | None = None
    try:
        fd = os.open(os.fspath(absolute), flags)
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            _fail(f"{where} changed to a non-regular file")
        identity = (before.st_dev, before.st_ino)
        chunks: list[bytes] = []
        size = 0
        while True:
            chunk = os.read(fd, min(READ_CHUNK, maximum - size + 1))
            if not chunk:
                break
            size += len(chunk)
            if size > maximum:
                _fail(f"{where} exceeds the bounded size of {maximum} bytes")
            chunks.append(chunk)
        after = os.fstat(fd)
        if (after.st_dev, after.st_ino) != identity or after.st_size != size:
            _fail(f"{where} changed while being read")
        return absolute, b"".join(chunks)
    except StructuralProfileSourceManifestError:
        raise
    except OSError as exc:
        _fail(f"{where} cannot be read safely: {exc}")
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass


def _execute_generator_snapshot(path: Path, source: bytes) -> ModuleType:
    """Execute only the immutable generator bytes whose digest is recorded."""

    original_path = sys.path
    original_path_entries = original_path.copy()
    original_modules = sys.modules
    original_module_entries = original_modules.copy()
    try:
        module = ModuleType("_ck_structural_profile_generator_snapshot")
        module.__file__ = os.fspath(path)
        module.__package__ = ""
        module.__loader__ = None
        unavailable_dependency = _UnavailableGeneratorDependency(_GENERATOR_PUBLISH_MODULE)
        original_import = builtins.__import__

        def import_snapshot_dependency(
            name: str,
            globals: dict[str, Any] | None = None,
            locals: dict[str, Any] | None = None,
            fromlist: object = (),
            level: int = 0,
        ) -> Any:
            if level == 0 and name == _GENERATOR_PUBLISH_MODULE:
                return unavailable_dependency
            return original_import(name, globals, locals, fromlist, level)

        snapshot_builtins = dict(vars(builtins))
        snapshot_builtins["__import__"] = import_snapshot_dependency
        module.__dict__["__builtins__"] = snapshot_builtins
        code = compile(source, os.fspath(path), "exec", dont_inherit=True)
        exec(code, module.__dict__)
        return module
    except Exception as exc:
        _fail(f"active profile generator snapshot could not be executed: {exc}")
    finally:
        if sys.path is not original_path:
            sys.path = original_path
        original_path[:] = original_path_entries
        if sys.modules is not original_modules:
            sys.modules = original_modules
        original_modules.clear()
        original_modules.update(original_module_entries)


def _read_directory_file(
    root_fd: int,
    name: str,
    maximum: int,
    where: str,
) -> bytes:
    """Read one bounded regular child through an already-open directory."""

    fd: int | None = None
    try:
        fd = os.open(
            name,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=root_fd,
        )
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            _fail(f"{where} must be a regular file")
        if before.st_size > maximum:
            _fail(f"{where} exceeds the bounded size of {maximum} bytes")
        chunks: list[bytes] = []
        size = 0
        while True:
            chunk = os.read(fd, min(READ_CHUNK, maximum - size + 1))
            if not chunk:
                break
            size += len(chunk)
            if size > maximum:
                _fail(f"{where} exceeds the bounded size of {maximum} bytes")
            chunks.append(chunk)
        after = os.fstat(fd)
        if (
            (after.st_dev, after.st_ino) != (before.st_dev, before.st_ino)
            or after.st_size != size
        ):
            _fail(f"{where} changed while being rechecked")
        return b"".join(chunks)
    except StructuralProfileSourceManifestError:
        raise
    except OSError as exc:
        _fail(f"{where} cannot be rechecked safely: {exc}")
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass


def _scan_source_directory(
    root: Path,
    expected_entries: set[str],
    *,
    expected_directory_identity: tuple[int, int] | None = None,
    expected_hashes: dict[str, str] | None = None,
) -> _SourceDirectorySnapshot:
    """Inspect one exact directory through a retained no-follow descriptor."""

    absolute = _absolute_lexical(root, "source manifest directory")
    _reject_symlink_components(absolute, "source manifest directory")
    root_fd: int | None = None
    try:
        root_fd = os.open(
            os.fspath(absolute),
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
        )
        root_info = os.fstat(root_fd)
        if not stat.S_ISDIR(root_info.st_mode):
            _fail("source manifest parent is not a directory")
        directory_identity = (root_info.st_dev, root_info.st_ino)
        if (
            expected_directory_identity is not None
            and directory_identity != expected_directory_identity
        ):
            _fail("source manifest directory changed during validation")
        names = set(os.listdir(root_fd))
        if names != expected_entries:
            missing = sorted(expected_entries - names)
            extra = sorted(names - expected_entries)
            detail = []
            if missing:
                detail.append("missing " + ", ".join(missing))
            if extra:
                detail.append("extra " + ", ".join(extra))
            _fail(
                "source manifest directory does not contain the exact file set ("
                + "; ".join(detail)
                + ")"
            )
        for name in sorted(names):
            info = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
                _fail(f"source manifest directory contains an unsafe entry: {name}")
            if expected_hashes is not None:
                maximum = MAX_MANIFEST_BYTES if name == "manifest.json" else MAX_SOURCE_BYTES
                rechecked = _read_directory_file(
                    root_fd,
                    name,
                    maximum,
                    f"source manifest directory entry {name}",
                )
                if hashlib.sha256(rechecked).hexdigest() != expected_hashes.get(name):
                    _fail(f"source manifest directory entry changed during validation: {name}")
        if set(os.listdir(root_fd)) != expected_entries:
            _fail("source manifest directory inventory changed during validation")
        final_root_info = os.fstat(root_fd)
        current_path_info = absolute.lstat()
        if (
            not stat.S_ISDIR(current_path_info.st_mode)
            or (final_root_info.st_dev, final_root_info.st_ino) != directory_identity
            or (current_path_info.st_dev, current_path_info.st_ino) != directory_identity
        ):
            _fail("source manifest directory changed during validation")
        return _SourceDirectorySnapshot(
            path=absolute,
            device=directory_identity[0],
            inode=directory_identity[1],
            entries=tuple(sorted(names)),
        )
    except StructuralProfileSourceManifestError:
        raise
    except OSError as exc:
        _fail(f"source manifest directory cannot be inspected safely: {exc}")
    finally:
        if root_fd is not None:
            try:
                os.close(root_fd)
            except OSError:
                pass


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _reject_constant(token: str) -> None:
    raise ValueError(token)


def _load_json(data: bytes, where: str, generator: ModuleType) -> Any:
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
        generator._finite(value, where)
        return value
    except StructuralProfileSourceManifestError:
        raise
    except (AttributeError, UnicodeDecodeError, json.JSONDecodeError, RecursionError, TypeError, ValueError) as exc:
        _fail(f"{where} is not finite UTF-8 JSON: {exc}")


def _canonical(value: Any, where: str, *, source: bool, generator: ModuleType) -> bytes:
    try:
        return (
            generator.canonical_source_bytes(value)
            if source
            else generator.canonical_bytes(value)
        )
    except Exception as exc:
        _fail(f"{where} cannot be serialized as canonical generated JSON: {exc}")


def _object(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(f"{where} must be an object")
    return value


def _require_fields(value: dict[str, Any], expected: set[str], where: str) -> None:
    if set(value) != expected:
        missing = sorted(expected - set(value))
        extra = sorted(set(value) - expected)
        detail = []
        if missing:
            detail.append("missing " + ", ".join(missing))
        if extra:
            detail.append("unknown " + ", ".join(extra))
        _fail(f"{where} has invalid fields ({'; '.join(detail)})")


def _text(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value:
        _fail(f"{where} must be a non-empty string")
    return value


def _hash(value: Any, where: str) -> str:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        _fail(f"{where} must be a lowercase SHA-256 digest")
    return value


def _freeze_json(value: Any) -> Any:
    if isinstance(value, dict):
        return tuple((key, _freeze_json(value[key])) for key in sorted(value))
    if isinstance(value, list):
        return tuple(_freeze_json(item) for item in value)
    return value


def _tail_signature(value: Any, where: str) -> tuple[int, int, int, int, int]:
    if not isinstance(value, list) or len(value) != 5 or any(type(item) is not int for item in value):
        _fail(f"{where} must contain exactly five integers")
    return tuple(value)  # type: ignore[return-value]


def _canonical_repository_relative_path(path: Path, where: str) -> str:
    absolute = _absolute_lexical(path, where)
    try:
        relative = absolute.relative_to(REPOSITORY_ROOT)
    except ValueError:
        _fail(f"{where} is outside the repository")
    if not relative.parts or any(part in {"", ".", ".."} for part in relative.parts):
        _fail(f"{where} is not a canonical repository-relative path")
    return PurePosixPath(*relative.parts).as_posix()


def _generator_contract() -> tuple[_GeneratorSnapshot, str, tuple[str, ...], str, str]:
    expected_path = _absolute_lexical(
        EXPERIMENT_ROOT / "generate_structural_profile_sources.py",
        "active profile generator",
    )
    generator_path, generator_bytes = _read_regular_file(
        expected_path,
        MAX_GENERATOR_BYTES,
        "active profile generator",
    )
    if generator_path != expected_path:
        _fail(f"active profile generator path changed: {generator_path}")
    generator = _execute_generator_snapshot(generator_path, generator_bytes)
    try:
        mode = generator.DEFAULT_GENERATION_MODE
        candidate_format = generator.FORMAT
        suffix = generator.SOURCE_DOCUMENT_SUFFIX
        profile_ids = generator.ACTIVE_PROFILE_IDS
        profile_count = generator.PROFILE_COUNT
        historical_mode = generator.HISTORICAL_GENERATION_MODE
    except AttributeError as exc:
        _fail(f"active profile generator contract is incomplete: {exc}")
    if type(mode) is not str or not mode:
        _fail("active profile generator mode is invalid")
    if type(candidate_format) is not str or not candidate_format:
        _fail("active profile generator format is invalid")
    if type(suffix) is not str or not suffix:
        _fail("active profile generator source-document suffix is invalid")
    if type(historical_mode) is not str or not historical_mode or mode == historical_mode:
        _fail("active profile generator mode is not distinct from historical mode")
    if type(profile_count) is not int or profile_count != PROFILE_COUNT:
        _fail("active profile generator does not declare exactly five profiles")
    if type(profile_ids) is not tuple or len(profile_ids) != PROFILE_COUNT:
        _fail("active profile generator profile contract must contain exactly five IDs")
    if any(type(profile_id) is not str or PROFILE_ID_RE.fullmatch(profile_id) is None for profile_id in profile_ids):
        _fail("active profile generator profile contract contains an invalid ID")
    if len(set(profile_ids)) != PROFILE_COUNT:
        _fail("active profile generator profile contract contains duplicate IDs")
    try:
        neutral_id = generator.STANDARD_NEUTRAL_PROFILE_ID
    except AttributeError as exc:
        _fail(f"active profile generator contract is missing the neutral profile ID: {exc}")
    if neutral_id != profile_ids[0]:
        _fail("active profile generator profile contract is not neutral-first")
    try:
        generated_count, generated_ids = generator._profile_contract(mode)
    except Exception as exc:
        _fail(f"active profile generator mode is invalid: {exc}")
    if generated_count != PROFILE_COUNT or tuple(generated_ids or ()) != profile_ids:
        _fail("active profile generator mode does not own the exact five-profile order")

    return _GeneratorSnapshot(generator, generator_path, generator_bytes), mode, profile_ids, candidate_format, suffix


def _generated_source_bytes(
    candidate: dict[str, Any],
    base_source: dict[str, Any],
    mode: str,
    profile_ids: tuple[str, ...],
    base_document: str,
    base_namespace: str,
    suffix: str,
    generator: ModuleType,
) -> tuple[tuple[bytes, ...], tuple[tuple[str, str, tuple[int, int, int, int, int]], ...]]:
    try:
        generated = generator.generate_sources(candidate, base_source, mode=mode)
    except Exception as exc:
        _fail(f"checked-in candidate/base could not regenerate profile sources: {exc}")
    if type(generated) is not list or len(generated) != PROFILE_COUNT:
        _fail("active generator did not produce exactly five profile documents")

    generated_bytes: list[bytes] = []
    generated_identity: list[tuple[str, str, tuple[int, int, int, int, int]]] = []
    for index, raw_source in enumerate(generated):
        where = f"regenerated source[{index}]"
        source = _object(raw_source, where)
        metadata = _object(source.get("source"), f"{where}.source")
        _require_fields(metadata, {"dependencies", "document", "namespace"}, f"{where}.source")
        profile_id = profile_ids[index]
        expected_document = f"{base_document}__{suffix}__{profile_id}"
        if metadata.get("document") != expected_document or metadata.get("namespace") != base_namespace:
            _fail(f"{where} source provenance does not bind the exact profile document")
        try:
            signature = _tail_signature(
                list(generator.tail_signature(source)),
                f"{where}.tail_signature",
            )
            data = _canonical(source, where, source=True, generator=generator)
        except StructuralProfileSourceManifestError:
            raise
        except Exception as exc:
            _fail(f"{where} has an invalid generated source shape: {exc}")
        if len(data) == 0 or len(data) > MAX_SOURCE_BYTES:
            _fail(f"{where} exceeds the bounded source size of {MAX_SOURCE_BYTES} bytes")
        generated_bytes.append(data)
        generated_identity.append((expected_document, base_namespace, signature))
    return tuple(generated_bytes), tuple(generated_identity)


def _validate(manifest_path: Path) -> SourceManifestValidationResult:
    generator_snapshot, mode, profile_ids, candidate_format, suffix = _generator_contract()
    generator = generator_snapshot.module
    absolute_manifest = _absolute_lexical(manifest_path, "source manifest")
    if absolute_manifest.name != "manifest.json":
        _fail("source manifest must be named manifest.json")
    root = absolute_manifest.parent
    expected_entries = {"manifest.json", *(f"{profile_id}.json" for profile_id in profile_ids)}
    source_directory = _scan_source_directory(root, expected_entries)
    manifest_path, manifest_bytes = _read_regular_file(
        absolute_manifest,
        MAX_MANIFEST_BYTES,
        "source manifest",
    )
    manifest_value = _load_json(manifest_bytes, "source manifest", generator)
    if manifest_bytes != _canonical(manifest_value, "source manifest", source=False, generator=generator):
        _fail("source manifest is not the canonical generated JSON")
    manifest = _object(manifest_value, "source manifest")
    _require_fields(manifest, {"candidate_format", "format", "profiles", "source"}, "source manifest")
    if manifest["format"] != SOURCE_MANIFEST_FORMAT:
        _fail(f"source manifest format must be {SOURCE_MANIFEST_FORMAT}")
    if manifest["candidate_format"] != candidate_format:
        _fail("source manifest candidate format is not the active generator format")

    source_lineage = _object(manifest["source"], "source manifest.source")
    _require_fields(
        source_lineage,
        {"base_document", "base_namespace", "candidate_sha256", "source_sha256"},
        "source manifest.source",
    )
    base_document = _text(source_lineage["base_document"], "source manifest.source.base_document")
    base_namespace = _text(source_lineage["base_namespace"], "source manifest.source.base_namespace")
    candidate_sha256 = _hash(source_lineage["candidate_sha256"], "source manifest.source.candidate_sha256")
    base_source_sha256 = _hash(source_lineage["source_sha256"], "source manifest.source.source_sha256")

    try:
        candidate_path_value = generator.DEFAULT_CANDIDATE
        base_source_path_value = generator.DEFAULT_SOURCE
    except AttributeError as exc:
        _fail(f"active profile generator input paths are incomplete: {exc}")
    candidate_path, candidate_bytes = _read_regular_file(
        _absolute_lexical(candidate_path_value, "checked-in candidate"),
        MAX_UPSTREAM_BYTES,
        "checked-in candidate",
    )
    base_source_path, base_source_bytes = _read_regular_file(
        _absolute_lexical(base_source_path_value, "checked-in base source"),
        MAX_UPSTREAM_BYTES,
        "checked-in base source",
    )
    actual_candidate_sha256 = hashlib.sha256(candidate_bytes).hexdigest()
    actual_base_source_sha256 = hashlib.sha256(base_source_bytes).hexdigest()
    if candidate_sha256 != actual_candidate_sha256:
        _fail("source manifest candidate hash does not match the checked-in candidate table")
    if base_source_sha256 != actual_base_source_sha256:
        _fail("source manifest base-source hash does not match the checked-in base source")

    candidate = _object(_load_json(candidate_bytes, "checked-in candidate", generator), "checked-in candidate")
    base_source = _object(_load_json(base_source_bytes, "checked-in base source", generator), "checked-in base source")
    candidate_base = _object(candidate.get("base_source"), "checked-in candidate.base_source")
    _require_fields(candidate_base, {"document", "namespace", "path", "sha256"}, "checked-in candidate.base_source")
    candidate_base_sha256 = _hash(candidate_base["sha256"], "checked-in candidate.base_source.sha256")
    if candidate_base_sha256 != actual_base_source_sha256:
        _fail("checked-in candidate base-source hash does not match the checked-in base source")
    expected_base_source_relative = _canonical_repository_relative_path(
        base_source_path,
        "active generator default source",
    )
    if candidate_base["path"] != expected_base_source_relative:
        _fail("checked-in candidate base-source path does not match the active generator default source")
    base_identity = _object(base_source.get("source"), "checked-in base source.source")
    _require_fields(base_identity, {"dependencies", "document", "namespace"}, "checked-in base source.source")
    if base_identity["document"] != base_document or base_identity["namespace"] != base_namespace:
        _fail("source manifest base-source identity does not match the checked-in base source")
    if candidate_base["document"] != base_document or candidate_base["namespace"] != base_namespace:
        _fail("checked-in candidate base-source identity does not match the checked-in base source")

    generated_bytes, generated_identity = _generated_source_bytes(
        candidate,
        base_source,
        mode,
        profile_ids,
        base_document,
        base_namespace,
        suffix,
        generator,
    )
    profiles = manifest["profiles"]
    if type(profiles) is not list or len(profiles) != PROFILE_COUNT:
        _fail("source manifest must contain exactly five profiles")
    if [item.get("id") if isinstance(item, dict) else None for item in profiles] != list(profile_ids):
        _fail("source manifest profiles are not in the exact required order")

    records: list[GeneratedSourceRecord] = []
    expected_profile_records: list[dict[str, Any]] = []
    for index, raw_profile in enumerate(profiles):
        where = f"source manifest.profiles[{index}]"
        profile = _object(raw_profile, where)
        _require_fields(profile, {"bytes", "document", "file", "id", "sha256", "tail_signature"}, where)
        profile_id = profile_ids[index]
        if profile["id"] != profile_id:
            _fail(f"{where}.id is not in the exact required order")
        expected_document, expected_namespace, expected_tail = generated_identity[index]
        if profile["document"] != expected_document:
            _fail(f"{where}.document does not bind its profile id")
        expected_file = f"{profile_id}.json"
        file_value = profile["file"]
        if (
            not isinstance(file_value, str)
            or "\\" in file_value
            or "\x00" in file_value
            or file_value != expected_file
            or PurePosixPath(file_value).parts != (expected_file,)
        ):
            _fail(f"{where}.file is not the canonical profile path")
        byte_count = profile["bytes"]
        if type(byte_count) is not int or byte_count <= 0 or byte_count > MAX_SOURCE_BYTES:
            _fail(f"{where}.bytes is outside the bounded source size")
        expected_bytes = len(generated_bytes[index])
        if byte_count != expected_bytes:
            _fail(f"{where}.bytes does not match the canonical generated source")
        expected_hash = _hash(profile["sha256"], f"{where}.sha256")
        generated_hash = hashlib.sha256(generated_bytes[index]).hexdigest()
        if expected_hash != generated_hash:
            _fail(f"{where}.sha256 does not match the canonical generated source")
        claimed_tail = _tail_signature(profile["tail_signature"], f"{where}.tail_signature")
        if claimed_tail != expected_tail:
            _fail(f"{where}.tail_signature does not match the canonical generated source")

        source_path, source_bytes = _read_regular_file(
            root / expected_file,
            MAX_SOURCE_BYTES,
            f"{where}.file",
        )
        source_value = _load_json(source_bytes, f"{where}.file", generator)
        if source_bytes != _canonical(source_value, f"{where}.file", source=True, generator=generator):
            _fail(f"{where}.file is not the canonical generated JSON")
        if source_bytes != generated_bytes[index]:
            _fail(f"{where}.file does not match the canonical checked-in candidate/base generator output")
        actual_hash = hashlib.sha256(source_bytes).hexdigest()
        if len(source_bytes) != byte_count or actual_hash != expected_hash:
            _fail(f"{where}.file does not match its manifest integrity metadata")
        source_object = _object(source_value, f"{where}.file")
        source_metadata = _object(source_object.get("source"), f"{where}.file.source")
        _require_fields(source_metadata, {"dependencies", "document", "namespace"}, f"{where}.file.source")
        if source_metadata["document"] != expected_document or source_metadata["namespace"] != expected_namespace:
            _fail(f"{where}.file source provenance does not match its profile record")
        actual_tail = _tail_signature(
            list(generator.tail_signature(source_object)),
            f"{where}.file.tail_signature",
        )
        if actual_tail != claimed_tail:
            _fail(f"{where}.tail_signature does not match its source document")
        provenance = SourceProvenance(
            document=source_metadata["document"],
            namespace=source_metadata["namespace"],
            dependencies=_freeze_json(source_metadata["dependencies"]),
        )
        records.append(
            GeneratedSourceRecord(
                id=profile_id,
                path=source_path,
                document=expected_document,
                namespace=expected_namespace,
                sha256=actual_hash,
                bytes=len(source_bytes),
                tail_signature=actual_tail,
                provenance=provenance,
            )
        )
        expected_profile_records.append(
            {
                "bytes": expected_bytes,
                "document": expected_document,
                "file": expected_file,
                "id": profile_id,
                "sha256": generated_hash,
                "tail_signature": list(expected_tail),
            }
        )

    expected_manifest = {
        "candidate_format": candidate_format,
        "format": SOURCE_MANIFEST_FORMAT,
        "profiles": expected_profile_records,
        "source": {
            "base_document": base_document,
            "base_namespace": base_namespace,
            "candidate_sha256": actual_candidate_sha256,
            "source_sha256": actual_base_source_sha256,
        },
    }
    if manifest != expected_manifest:
        _fail("source manifest claims do not match the canonical checked-in generator output")

    final_source_hashes = {
        "manifest.json": hashlib.sha256(manifest_bytes).hexdigest(),
        **{f"{record.id}.json": record.sha256 for record in records},
    }
    _scan_source_directory(
        root,
        expected_entries,
        expected_directory_identity=source_directory.identity,
        expected_hashes=final_source_hashes,
    )

    generator_sha256 = hashlib.sha256(generator_snapshot.bytes).hexdigest()
    generator_lineage = GeneratorLineage(
        path=generator_snapshot.path,
        sha256=generator_sha256,
        bytes=len(generator_snapshot.bytes),
        mode=mode,
        format=candidate_format,
        source_document_suffix=suffix,
        profile_ids=profile_ids,
        candidate_path=candidate_path,
        base_source_path=base_source_path,
        candidate_sha256=actual_candidate_sha256,
        base_source_sha256=actual_base_source_sha256,
    )
    manifest_lineage = ManifestLineage(
        path=manifest_path,
        sha256=hashlib.sha256(manifest_bytes).hexdigest(),
        bytes=len(manifest_bytes),
        format=manifest["format"],
        candidate_format=manifest["candidate_format"],
        candidate_sha256=candidate_sha256,
        base_source_sha256=base_source_sha256,
        base_document=base_document,
        base_namespace=base_namespace,
        profile_ids=profile_ids,
    )
    return SourceManifestValidationResult(
        manifest=manifest_lineage,
        generator=generator_lineage,
        profile_ids=profile_ids,
        sources=tuple(records),
    )


def validate_structural_profile_source_manifest(
    manifest_path: os.PathLike[str] | str,
) -> SourceManifestValidationResult:
    """Validate one active ``manifest.json`` and its exact five source files."""

    try:
        return _validate(Path(os.fspath(manifest_path)))
    except StructuralProfileSourceManifestError:
        raise
    except (OSError, TypeError, ValueError, AttributeError, KeyError, IndexError, RecursionError, OverflowError) as exc:
        raise StructuralProfileSourceManifestError(f"source manifest validation failed: {exc}") from exc


validate_source_manifest = validate_structural_profile_source_manifest
validate = validate_structural_profile_source_manifest


def _implementation_source_snapshot() -> _ImplementationSourceSnapshot:
    """Return the retained bytes that define all callable validator behavior."""

    snapshot = globals().get("_VALIDATOR_IMPLEMENTATION_SOURCE_SNAPSHOT")
    if not isinstance(snapshot, _ImplementationSourceSnapshot):
        _fail("validator implementation source snapshot is unavailable")
    if hashlib.sha256(snapshot.source_bytes).hexdigest() != snapshot.sha256:
        _fail("validator implementation source snapshot is invalid")
    return snapshot


def _implementation_source_identity() -> dict[str, Any]:
    return _implementation_source_snapshot().identity


def _bootstrap_implementation_source() -> None:
    """Re-execute this module from one retained source descriptor snapshot."""

    source_path, source_bytes = _read_regular_file(
        Path(__file__),
        MAX_IMPLEMENTATION_BYTES,
        "structural source-manifest validator implementation",
    )
    if not source_bytes:
        _fail("structural source-manifest validator implementation is empty")
    source_sha256 = hashlib.sha256(source_bytes).hexdigest()
    globals()["_VALIDATOR_SNAPSHOT_EXECUTION"] = True
    globals()["_VALIDATOR_SNAPSHOT_PATH"] = source_path
    globals()["_VALIDATOR_SNAPSHOT_BYTES"] = source_bytes
    globals()["_VALIDATOR_SNAPSHOT_SHA256"] = source_sha256
    code = compile(source_bytes, os.fspath(source_path), "exec", dont_inherit=True)
    exec(code, globals())


__all__ = [
    "GeneratedSourceRecord",
    "GeneratorLineage",
    "ManifestLineage",
    "PROFILE_COUNT",
    "SOURCE_MANIFEST_FORMAT",
    "SourceManifestValidationError",
    "SourceManifestValidationResult",
    "SourceProvenance",
    "StructuralProfileSourceManifestError",
    "validate",
    "validate_source_manifest",
    "validate_structural_profile_source_manifest",
]


if globals().get("_VALIDATOR_SNAPSHOT_EXECUTION", False):
    _VALIDATOR_IMPLEMENTATION_SOURCE_SNAPSHOT = _ImplementationSourceSnapshot(
        path=globals()["_VALIDATOR_SNAPSHOT_PATH"],
        source_bytes=globals()["_VALIDATOR_SNAPSHOT_BYTES"],
        sha256=globals()["_VALIDATOR_SNAPSHOT_SHA256"],
    )
else:
    _bootstrap_implementation_source()

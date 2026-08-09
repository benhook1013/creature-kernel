"""Headless CK-KICK-010 build command.

This adapter joins the disposable resolver, geometry, export, and artifact
seams.  It intentionally exposes no production compiler contract: the command
publishes a small, complete debug bundle or a complete diagnostics-only bundle
and keeps all failures structured and machine-readable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import stat
import sys
from typing import Any, Mapping, Sequence

from . import artifacts, resolver
from .diagnostics import Diagnostic, Phase, Severity, ValidationResult
from .export import (
    ExportError,
    export_transform_metadata,
    require_valid_export,
    semantic_regions_bytes,
    serialize_ply,
)
from .geometry import GeometryConfig, GeometryError, SurfaceResult, build_surface


VALID_ARTIFACT_NAMES: tuple[str, ...] = (
    "diagnostics.json",
    "manifest.json",
    "mesh.ply",
    "resolved_graph.json",
    "semantic_regions.json",
)
INVALID_ARTIFACT_NAMES: tuple[str, ...] = ("diagnostics.json", "manifest.json")
COMPILER_IDENTITY = "ck-kick-010-disposable-python-host-v1"


class CLIUsageError(ValueError):
    """An argument error represented on stdout as one result JSON object."""


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # pragma: no cover - exercised by smoke users
        raise CLIUsageError(message)


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="ck_spike", add_help=True)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build")
    build.add_argument("--input", required=True, type=Path)
    build.add_argument("--output", required=True, type=Path)
    build.add_argument("--samples-per-axis", type=int, default=GeometryConfig().samples_per_axis)
    build.add_argument("--padding", type=float, default=GeometryConfig().padding)
    build.add_argument("--smooth-min-k", type=float, default=GeometryConfig().smooth_min_k)
    return parser


def _diagnostic(
    code: str,
    phase: Phase,
    path: str,
    message: str,
    *,
    related: Sequence[str] = (),
) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=Severity.ERROR,
        phase=phase,
        path=path,
        related_source_labels=tuple(related),
        message=message,
    )


def _stable_diagnostic(diagnostic: Diagnostic) -> dict[str, Any]:
    """Keep resolver/artifact diagnostics structured without leaking input paths."""

    result = diagnostic.to_dict()
    if diagnostic.code == "INPUT_READ_ERROR":
        # resolver.resolve_file includes the OS exception's path in its prose;
        # the code and phase carry the useful stable information and the bundle
        # must never embed an absolute input path.
        result["message"] = "input could not be read"
    return result


def _diagnostics_bytes(status: str, diagnostics: Sequence[Diagnostic]) -> bytes:
    return artifacts.canonical_json_bytes(
        {
            "format": "ck-kick-010-diagnostics-v1",
            "status": status,
            "diagnostics": [_stable_diagnostic(item) for item in diagnostics],
        }
    )


def _source_identity() -> str:
    """Hash sorted ``ck_spike/*.py`` names and bytes without Git or paths."""

    root = Path(__file__).resolve().parent
    digest = hashlib.sha256()
    for source in sorted(root.glob("*.py"), key=lambda item: item.name):
        name = source.name.encode("utf-8")
        data = source.read_bytes()
        # Length framing makes the concatenation unambiguous while retaining
        # only the relative source name and source bytes in the digest input.
        digest.update(len(name).to_bytes(8, "big"))
        digest.update(name)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return f"sha256:{digest.hexdigest()}"


def _build_identity(document: Any, config: GeometryConfig, *, spike_revision: Any, seed: Any) -> dict[str, Any]:
    try:
        artifacts.canonical_json_bytes(document)
    except (TypeError, ValueError):
        # A malformed JSON value (for example non-standard NaN accepted by
        # Python's decoder) is still an input-validation failure.  Preserve a
        # deterministic identity record without copying that value into the
        # bundle.
        document = None
        spike_revision = None
        seed = None
    return artifacts.build_identity(
        spike_revision=spike_revision,
        seed=seed,
        input_payload=document,
        config_payload=config.to_dict(),
        compiler_identity=COMPILER_IDENTITY,
        source_identity=_source_identity(),
    )


def _field(document: Any, name: str, default: Any = None) -> Any:
    value = document.get(name, default) if isinstance(document, Mapping) else default
    try:
        artifacts.canonical_json_bytes(value)
    except (TypeError, ValueError):
        return default
    return value


def _manifest_bytes(
    non_manifest: Mapping[str, bytes],
    *,
    document: Any,
    status: str,
    config: GeometryConfig,
    graph: Any | None = None,
    surface: SurfaceResult | None = None,
    export_result: Any | None = None,
) -> bytes:
    manifest = artifacts.build_manifest(non_manifest)
    manifest.update(
        {
            "fixture_id": _field(document, "fixture_id"),
            "status": status,
            "spike_revision": _field(document, "spike_revision"),
            "seed": _field(document, "seed"),
            "geometry_config": config.to_dict(),
            "build_identity": _build_identity(
                document,
                config,
                spike_revision=_field(document, "spike_revision"),
                seed=_field(document, "seed"),
            ),
            "coordinate_convention": _field(document, "coordinate_convention"),
            "grid": surface.grid.to_dict() if surface is not None else None,
            "metrics": surface.metrics.to_dict() if surface is not None else None,
            "export": export_transform_metadata(export_result) if export_result is not None else None,
            "resolved_graph_node_count": len(graph.nodes) if graph is not None else 0,
        }
    )
    return artifacts.canonical_json_bytes(manifest)


def _bundle_file_names(directory: Path) -> tuple[str, ...]:
    names: list[str] = []
    for path in directory.rglob("*"):
        relative = path.relative_to(directory).as_posix()
        try:
            mode = path.lstat().st_mode
        except OSError:
            # Make an inventory race fail the exact-shape check without
            # attempting to hash a path whose type could not be inspected.
            return ("<unreadable-staged-path>",)
        if stat.S_ISREG(mode):
            names.append(relative)
        elif stat.S_ISDIR(mode):
            # A complete bundle has no nested directories.  Keep this marker so
            # the exact-shape validator rejects an otherwise hidden directory.
            names.append(relative + "/")
        else:
            # ``Path.is_file`` follows symlinks and would let a link to an
            # external file reach the hash/publication path.  Use a marker that
            # cannot equal an expected regular artifact name for every other
            # inode type (symlink, device, FIFO, socket, and so on).
            names.append(relative + "\x00")
    return tuple(sorted(names))


def _validate_staged_bundle(directory: Path, *, status: str) -> bool:
    expected = VALID_ARTIFACT_NAMES if status == "valid" else INVALID_ARTIFACT_NAMES
    if _bundle_file_names(directory) != expected:
        return False
    manifest_path = directory / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        hashes = manifest.get("artifacts")
        if not isinstance(hashes, dict) or set(hashes) != set(expected) - {"manifest.json"}:
            return False
        if manifest.get("status") != status:
            return False
        for name in sorted(hashes):
            if not isinstance(hashes[name], str) or artifacts.sha256_file(directory / name) != hashes[name]:
                return False
        # Every JSON artifact is canonical.  This catches accidental locale,
        # whitespace, and key-order drift before publication.
        for name in expected:
            if name.endswith(".json"):
                payload = json.loads((directory / name).read_text(encoding="utf-8"))
                if artifacts.canonical_json_bytes(payload) != (directory / name).read_bytes():
                    return False
    except (OSError, ValueError, TypeError, KeyError):
        return False
    return True


def _publish(
    output: Path,
    files: Mapping[str, bytes],
    *,
    status: str,
) -> artifacts.PublicationResult:
    return artifacts.publish_bundle(
        output,
        files=files,
        validator=lambda staging: _validate_staged_bundle(staging, status=status),
    )


def _result(
    *,
    status: str,
    exit_code: int,
    document: Any = None,
    artifact_names: Sequence[str] = (),
    diagnostics: Sequence[Diagnostic] = (),
) -> dict[str, Any]:
    return {
        "status": status,
        "exit_code": exit_code,
        "fixture_id": _field(document, "fixture_id"),
        "artifact_names": list(artifact_names),
        "diagnostic_codes": [item.code for item in diagnostics],
    }


def _emit(value: Mapping[str, Any]) -> None:
    sys.stdout.write(artifacts.canonical_json_text(dict(value)))


def _load_and_resolve(path: Path) -> tuple[Any, ValidationResult]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        # Keep the resolver's typed input diagnostic boundary.  The CLI later
        # redacts only its path-bearing human message for deterministic output.
        result = resolver.resolve_file(path)
        return None, result
    except UnicodeError:
        return None, ValidationResult(
            diagnostics=(
                _diagnostic(
                    "INPUT_READ_ERROR",
                    Phase.VALIDATION,
                    "/",
                    "input could not be decoded as UTF-8",
                ),
            )
        )
    try:
        document = json.loads(text)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None, resolver.resolve_json(text)
    return document, resolver.resolve_document(document)


def _diagnostics_only(
    output: Path,
    document: Any,
    config: GeometryConfig,
    diagnostics: Sequence[Diagnostic],
) -> tuple[dict[str, Any], int]:
    payload = _diagnostics_bytes("invalid", diagnostics)
    manifest = _manifest_bytes(
        {"diagnostics.json": payload},
        document=document,
        status="invalid",
        config=config,
    )
    files = {"diagnostics.json": payload, "manifest.json": manifest}
    publication = _publish(output, files, status="invalid")
    return (
        _result(
            status="invalid",
            exit_code=2,
            document=document,
            artifact_names=publication.artifact_names,
            diagnostics=diagnostics,
        ),
        2,
    )


def _build(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    try:
        config = GeometryConfig(
            samples_per_axis=args.samples_per_axis,
            padding=args.padding,
            smooth_min_k=args.smooth_min_k,
        )
    except (TypeError, ValueError, OverflowError):
        diagnostic = _diagnostic(
            "INVALID_GEOMETRY_CONFIG",
            Phase.VALIDATION,
            "/geometry_config",
            "geometry overrides must be finite and within the GeometryConfig bounds",
        )
        # No document is available yet, but a valid output path can still
        # receive the expected diagnostics-only bundle.
        return _diagnostics_only(args.output, None, GeometryConfig(), (diagnostic,))

    document, validation = _load_and_resolve(args.input)
    if not validation.ok:
        return _diagnostics_only(args.output, document, config, validation.diagnostics)
    graph = validation.require_graph()

    try:
        surface = build_surface(graph, config)
        export_result = require_valid_export(surface, graph)
        mesh_bytes = serialize_ply(surface)
        regions_bytes = semantic_regions_bytes(surface)
    except (GeometryError, ExportError) as error:
        diagnostics = error.diagnostics
        return (
            _result(status="failed", exit_code=3, document=document, diagnostics=diagnostics),
            3,
        )
    except Exception:
        diagnostic = _diagnostic(
            "UNEXPECTED_FAILURE",
            Phase.ARTIFACT,
            "/build",
            "unexpected build failure",
        )
        return (
            _result(status="failed", exit_code=4, document=document, diagnostics=(diagnostic,)),
            4,
        )

    graph_bytes = artifacts.canonical_json_bytes(graph.to_dict())
    diagnostics_bytes = _diagnostics_bytes("valid", ())
    regions = {"semantic_regions.json": regions_bytes}
    non_manifest = {
        "resolved_graph.json": graph_bytes,
        "mesh.ply": mesh_bytes,
        **regions,
        "diagnostics.json": diagnostics_bytes,
    }
    manifest = _manifest_bytes(
        non_manifest,
        document=document,
        status="valid",
        config=config,
        graph=graph,
        surface=surface,
        export_result=export_result,
    )
    files = {**non_manifest, "manifest.json": manifest}
    try:
        publication = _publish(args.output, files, status="valid")
    except artifacts.ArtifactError as error:
        diagnostics = error.diagnostics
        return (
            _result(status="failed", exit_code=4, document=document, diagnostics=diagnostics),
            4,
        )
    except Exception:
        diagnostic = _diagnostic(
            "UNEXPECTED_FAILURE",
            Phase.PUBLICATION,
            "/publication",
            "unexpected publication failure",
        )
        return (
            _result(status="failed", exit_code=4, document=document, diagnostics=(diagnostic,)),
            4,
        )
    return (
        _result(
            status="valid",
            exit_code=0,
            document=document,
            artifact_names=publication.artifact_names,
        ),
        0,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run ``build`` and emit exactly one canonical JSON result on stdout."""

    try:
        args = _parser().parse_args(argv)
        if args.command != "build":
            raise CLIUsageError("only the build command is supported")
        value, code = _build(args)
    except CLIUsageError:
        diagnostic = _diagnostic(
            "CLI_USAGE_ERROR",
            Phase.VALIDATION,
            "/arguments",
            "usage must be: build --input PATH --output PATH",
        )
        value, code = _result(status="failed", exit_code=2, diagnostics=(diagnostic,)), 2
    except artifacts.ArtifactError as error:
        # This also covers diagnostics-only publication failures, including an
        # existing/protected output target.  The artifact seam has already
        # cleaned its own staging path and never overwrites a target.
        value, code = _result(status="failed", exit_code=4, diagnostics=error.diagnostics), 4
    except Exception:
        diagnostic = _diagnostic(
            "UNEXPECTED_FAILURE",
            Phase.ARTIFACT,
            "/build",
            "unexpected build failure",
        )
        value, code = _result(status="failed", exit_code=4, diagnostics=(diagnostic,)), 4
    _emit(value)
    return code


__all__ = ["main"]

#!/usr/bin/env python3
"""Publish a validated image manifest as an immutable visual-review session."""

from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import os
import re
import secrets
import stat
import sys
from pathlib import Path
from typing import Any

from common import (
    SourceReference,
    ValidationError,
    canonical_json,
    ensure_root,
    open_source_reference,
    read_rich_manifest,
    require_secure_fs_support,
)


class PublishError(RuntimeError):
    pass


COPY_CHUNK = 64 * 1024
STAGING_ATTEMPTS = 100
RENAME_NOREPLACE = 1


def _open_directory(parent_fd: int | None, path_or_name: Path | str, where: str) -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = None
    try:
        if parent_fd is None:
            absolute = Path(path_or_name).absolute()
            fd = os.open("/", flags)
            for component in absolute.parts[1:]:
                following = os.open(component, flags, dir_fd=fd)
                os.close(fd)
                fd = following
        else:
            fd = os.open(path_or_name, flags, dir_fd=parent_fd)
        info = os.fstat(fd)
        if not stat.S_ISDIR(info.st_mode):
            os.close(fd)
            fd = None
            raise ValidationError(f"{where} is not a regular directory")
        return fd
    except ValidationError:
        if fd is not None:
            os.close(fd)
        raise
    except OSError as exc:
        if fd is not None:
            os.close(fd)
        raise ValidationError(f"{where} is unavailable or changed") from exc


def _copy_source(
    source: SourceReference,
    destination_fd: int,
    destination_name: str,
    where: str,
) -> tuple[int, str]:
    """Copy from one already-validated descriptor, never reopening its path."""

    digest = hashlib.sha256()
    size = 0
    output_fd = os.open(
        destination_name,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
        dir_fd=destination_fd,
    )
    output_identity: tuple[int, int] | None = None
    try:
        output_info = os.fstat(output_fd)
        output_identity = (output_info.st_dev, output_info.st_ino)
        with open_source_reference(source, where) as stream:
            with os.fdopen(output_fd, "wb") as output:
                output_fd = None
                while True:
                    chunk = stream.read(COPY_CHUNK)
                    if not chunk:
                        break
                    size += len(chunk)
                    digest.update(chunk)
                    output.write(chunk)
                os.fchmod(output.fileno(), 0o644)
    except Exception:
        try:
            current = os.stat(destination_name, dir_fd=destination_fd, follow_symlinks=False)
            if output_identity is not None and (current.st_dev, current.st_ino) == output_identity:
                os.unlink(destination_name, dir_fd=destination_fd)
        except OSError:
            pass
        raise
    finally:
        if output_fd is not None:
            os.close(output_fd)
    return size, digest.hexdigest()


def _write_owned(parent_fd: int, name: str, text: str) -> None:
    # The entry is created inside a freshly-created, invocation-owned staging
    # directory and is never reopened through the original root path.
    output_fd = os.open(
        name,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o644,
        dir_fd=parent_fd,
    )
    output_identity: tuple[int, int] | None = None
    try:
        output_info = os.fstat(output_fd)
        output_identity = (output_info.st_dev, output_info.st_ino)
        with os.fdopen(output_fd, "w", encoding="utf-8", newline="\n") as output:
            output_fd = None
            output.write(text)
    except Exception:
        try:
            current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            if output_identity is not None and (current.st_dev, current.st_ino) == output_identity:
                os.unlink(name, dir_fd=parent_fd)
        except OSError:
            pass
        raise
    finally:
        if output_fd is not None:
            os.close(output_fd)


def _rename_noreplace(
    source_dir_fd: int,
    source_name: str,
    destination_dir_fd: int,
    destination_name: str,
) -> None:
    """Atomically move a directory without replacing an existing entry."""

    if not sys.platform.startswith("linux"):
        raise OSError(errno.ENOTSUP, "atomic no-replace directory rename unavailable")
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    if renameat2 is None:
        raise OSError(errno.ENOTSUP, "atomic no-replace directory rename unavailable")
    renameat2.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    renameat2.restype = ctypes.c_int
    result = renameat2(
        source_dir_fd,
        os.fsencode(source_name),
        destination_dir_fd,
        os.fsencode(destination_name),
        RENAME_NOREPLACE,
    )
    if result != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), destination_name)


def _create_staging(root_fd: int, review_id: str) -> tuple[str, int]:
    """Create and open a unique staging directory relative to the open root."""

    prefix = f".{review_id}.publish-"
    for _ in range(STAGING_ATTEMPTS):
        name = prefix + secrets.token_hex(16)
        try:
            os.mkdir(name, mode=0o700, dir_fd=root_fd)
        except FileExistsError:
            continue

        staging_fd: int | None = None
        try:
            info = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
            if not stat.S_ISDIR(info.st_mode):
                raise ValidationError("publish staging is not a directory")
            staging_fd = _open_directory(root_fd, name, "publish staging")
            opened_info = os.fstat(staging_fd)
            if (opened_info.st_dev, opened_info.st_ino) != (info.st_dev, info.st_ino):
                os.close(staging_fd)
                staging_fd = None
                raise ValidationError("publish staging changed while being opened")
            return name, staging_fd
        except Exception:
            if staging_fd is not None:
                try:
                    os.close(staging_fd)
                except OSError:
                    pass
            # There is no safe directory-unlink-by-fd primitive here.  Keep
            # the hidden name rather than racing a replacement at that name.
            raise
    raise PublishError("could not create a unique publish staging directory")


def _cleanup_staging(
    staging_fd: int,
    assets_fd: int | None,
    assets_identity: tuple[int, int] | None,
    asset_stats: dict[str, tuple[int, int]],
    review_stat: tuple[int, int] | None,
) -> None:
    """Remove only owned staging contents through already-open descriptors."""

    if assets_fd is not None:
        for name, expected in asset_stats.items():
            try:
                info = os.stat(name, dir_fd=assets_fd, follow_symlinks=False)
                if (info.st_dev, info.st_ino) == expected:
                    os.unlink(name, dir_fd=assets_fd)
            except OSError:
                pass
        try:
            info = os.stat("assets", dir_fd=staging_fd, follow_symlinks=False)
            if assets_identity is not None and (info.st_dev, info.st_ino) == assets_identity:
                os.rmdir("assets", dir_fd=staging_fd)
        except OSError:
            pass
    if review_stat is not None:
        try:
            info = os.stat("review.json", dir_fd=staging_fd, follow_symlinks=False)
            if (info.st_dev, info.st_ino) == review_stat:
                os.unlink("review.json", dir_fd=staging_fd)
        except OSError:
            pass


def _close_fd(fd: int | None) -> None:
    if fd is not None:
        try:
            os.close(fd)
        except OSError:
            pass


def _validate_expected_sources(
    expected_sources: dict[str, dict[str, int | str]] | None,
    item_ids: set[str],
) -> dict[str, tuple[int, str]] | None:
    if expected_sources is None:
        return None
    if not isinstance(expected_sources, dict):
        raise ValidationError("expected_sources must be an object")
    if set(expected_sources) != item_ids:
        raise ValidationError("expected_sources must contain exactly one entry per item id")

    normalized: dict[str, tuple[int, str]] = {}
    for item_id, expected in expected_sources.items():
        where = f"expected_sources[{item_id!r}]"
        if not isinstance(expected, dict) or set(expected) != {"bytes", "sha256"}:
            raise ValidationError(f"{where} must contain exactly bytes and sha256")
        byte_count = expected["bytes"]
        if type(byte_count) is not int or byte_count < 0:
            raise ValidationError(f"{where}.bytes must be a non-negative integer")
        sha256 = expected["sha256"]
        if not isinstance(sha256, str) or re.fullmatch(r"[0-9a-f]{64}", sha256) is None:
            raise ValidationError(f"{where}.sha256 must be lowercase hexadecimal SHA-256")
        normalized[item_id] = (byte_count, sha256)
    return normalized


def publish_session(
    reviews_root: Path,
    source_manifest: Path,
    expected_sources: dict[str, dict[str, int | str]] | None = None,
) -> dict[str, Any]:
    """Publish one session and return the canonical machine-readable summary."""

    root = ensure_root(reviews_root)
    try:
        validated_root_info = os.stat(root, follow_symlinks=False)
    except OSError as exc:
        raise ValidationError("reviews root is unavailable or changed") from exc
    if not stat.S_ISDIR(validated_root_info.st_mode):
        raise ValidationError("reviews root must be a regular directory")
    validated_root_identity = (validated_root_info.st_dev, validated_root_info.st_ino)
    require_secure_fs_support()
    manifest_path = source_manifest.absolute()
    review, sources = read_rich_manifest(manifest_path)
    item_ids = {
        item["id"]
        for group in review["groups"]
        for item in group["items"]
    }
    normalized_expected_sources = _validate_expected_sources(expected_sources, item_ids)
    session = root / review["id"]
    if session.exists() or session.is_symlink():
        raise PublishError(f"session already exists: {review['id']}")

    root_fd = _open_directory(None, root, "reviews root")
    staging_name: str | None = None
    staging_fd: int | None = None
    staged_assets_fd = None
    assets_identity: tuple[int, int] | None = None
    asset_stats: dict[str, tuple[int, int]] = {}
    review_stat: tuple[int, int] | None = None
    installed = False
    try:
        opened_root_info = os.fstat(root_fd)
        if (opened_root_info.st_dev, opened_root_info.st_ino) != validated_root_identity:
            raise ValidationError("reviews root changed while being opened")
        staging_name, staging_fd = _create_staging(root_fd, review["id"])
        os.mkdir("assets", mode=0o755, dir_fd=staging_fd)
        staged_assets_fd = _open_directory(staging_fd, "assets", "staged assets")
        assets_info = os.fstat(staged_assets_fd)
        assets_identity = (assets_info.st_dev, assets_info.st_ino)
        for group in review["groups"]:
            for item in group["items"]:
                source = sources[item["id"]]
                destination_name = Path(item["image"]).name
                actual_bytes, actual_sha256 = _copy_source(
                    source, staged_assets_fd, destination_name, f"item {item['id']} source"
                )
                info = os.stat(destination_name, dir_fd=staged_assets_fd, follow_symlinks=False)
                asset_stats[destination_name] = (info.st_dev, info.st_ino)
                expected = (
                    normalized_expected_sources.get(item["id"])
                    if normalized_expected_sources is not None
                    else None
                )
                if expected is not None and (actual_bytes, actual_sha256) != expected:
                    raise PublishError(
                        f"item {item['id']} source integrity mismatch: "
                        f"expected {expected[0]} bytes/{expected[1]}, "
                        f"got {actual_bytes} bytes/{actual_sha256}"
                    )
        _write_owned(staging_fd, "review.json", canonical_json(review))
        review_info = os.stat("review.json", dir_fd=staging_fd, follow_symlinks=False)
        review_stat = (review_info.st_dev, review_info.st_ino)
        os.fchmod(staging_fd, 0o755)
        try:
            _rename_noreplace(root_fd, staging_name, root_fd, review["id"])
        except FileExistsError as exc:
            raise PublishError(f"session appeared during publish: {review['id']}") from exc
        installed = True
        staging_name = None
        _close_fd(staged_assets_fd)
        staged_assets_fd = None
        _close_fd(staging_fd)
        staging_fd = None
        _close_fd(root_fd)
        return {
            "schema_version": 1,
            "id": review["id"],
            "session": str(session),
            "review": str(session / "review.json"),
            "assets": len(sources),
        }
    except Exception:
        if staging_fd is not None and not installed:
            try:
                _cleanup_staging(
                    staging_fd,
                    staged_assets_fd,
                    assets_identity,
                    asset_stats,
                    review_stat,
                )
            except OSError:
                pass
        _close_fd(staged_assets_fd)
        _close_fd(staging_fd)
        _close_fd(root_fd)
        raise


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path, help="existing reviews root")
    parser.add_argument("--manifest", required=True, type=Path, help="rich manifest JSON file")
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        summary = publish_session(args.root, args.manifest)
    except (ValidationError, PublishError, OSError) as exc:
        print(f"publish failed: {exc}", file=sys.stderr)
        return 2
    print(canonical_json(summary), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Publish a validated image manifest as an immutable visual-review session."""

from __future__ import annotations

import argparse
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
    try:
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
    try:
        with os.fdopen(output_fd, "w", encoding="utf-8", newline="\n") as output:
            output_fd = None
            output.write(text)
    finally:
        if output_fd is not None:
            os.close(output_fd)


def _create_staging(root_fd: int, review_id: str) -> tuple[str, int, tuple[int, int]]:
    """Create and open a unique staging directory relative to the open root."""

    prefix = f".{review_id}.publish-"
    for _ in range(STAGING_ATTEMPTS):
        name = prefix + secrets.token_hex(16)
        try:
            os.mkdir(name, mode=0o700, dir_fd=root_fd)
        except FileExistsError:
            continue

        created_identity: tuple[int, int] | None = None
        staging_fd: int | None = None
        try:
            info = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
            if not stat.S_ISDIR(info.st_mode):
                raise ValidationError("publish staging is not a directory")
            created_identity = (info.st_dev, info.st_ino)
            staging_fd = _open_directory(root_fd, name, "publish staging")
            opened_info = os.fstat(staging_fd)
            if (opened_info.st_dev, opened_info.st_ino) != created_identity:
                raise ValidationError("publish staging changed while being opened")
            return name, staging_fd, created_identity
        except Exception:
            if staging_fd is not None:
                try:
                    os.close(staging_fd)
                except OSError:
                    pass
            if created_identity is not None:
                try:
                    info = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
                    if (
                        stat.S_ISDIR(info.st_mode)
                        and (info.st_dev, info.st_ino) == created_identity
                    ):
                        os.rmdir(name, dir_fd=root_fd)
                except OSError:
                    pass
            raise
    raise PublishError("could not create a unique publish staging directory")


def _cleanup_directory_fd(directory_fd: int) -> None:
    """Remove a staging tree through descriptors, without following entries."""

    for name in os.listdir(directory_fd):
        try:
            info = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        except OSError:
            continue
        identity = (info.st_dev, info.st_ino)
        if stat.S_ISDIR(info.st_mode):
            child_fd = None
            try:
                child_fd = _open_directory(directory_fd, name, "staging child")
                _cleanup_directory_fd(child_fd)
            except (OSError, ValidationError):
                continue
            finally:
                if child_fd is not None:
                    try:
                        os.close(child_fd)
                    except OSError:
                        pass
            try:
                current = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                if (current.st_dev, current.st_ino) == identity:
                    os.rmdir(name, dir_fd=directory_fd)
            except OSError:
                pass
        else:
            try:
                current = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                if (current.st_dev, current.st_ino) == identity:
                    os.unlink(name, dir_fd=directory_fd)
            except OSError:
                pass


def _cleanup_staging(
    root_fd: int,
    staging_name: str,
    staging_fd: int,
    staging_identity: tuple[int, int],
) -> None:
    """Remove only the identity-matching staging directory through open fds."""

    _cleanup_directory_fd(staging_fd)
    info = os.stat(staging_name, dir_fd=root_fd, follow_symlinks=False)
    if not stat.S_ISDIR(info.st_mode) or (info.st_dev, info.st_ino) != staging_identity:
        return
    os.rmdir(staging_name, dir_fd=root_fd)


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


def _cleanup_owned_session(
    root_fd: int,
    session_name: str,
    session_fd: int,
    assets_fd: int | None,
    asset_stats: dict[str, tuple[int, int]],
    review_stat: tuple[int, int] | None,
    session_identity: tuple[int, int] | None,
) -> None:
    """Remove only identity-matching files created by this invocation."""

    local_assets_fd = assets_fd
    try:
        if local_assets_fd is None:
            try:
                local_assets_fd = _open_directory(session_fd, "assets", "session assets")
            except ValidationError:
                local_assets_fd = None
        if local_assets_fd is not None:
            for name, expected in asset_stats.items():
                try:
                    info = os.stat(name, dir_fd=local_assets_fd, follow_symlinks=False)
                    if (info.st_dev, info.st_ino) == expected:
                        os.unlink(name, dir_fd=local_assets_fd)
                except OSError:
                    pass
            if assets_fd is None:
                try:
                    os.close(local_assets_fd)
                except OSError:
                    pass
        if review_stat is not None:
            try:
                info = os.stat("review.json", dir_fd=session_fd, follow_symlinks=False)
                if (info.st_dev, info.st_ino) == review_stat:
                    os.unlink("review.json", dir_fd=session_fd)
            except OSError:
                pass
        try:
            os.rmdir("assets", dir_fd=session_fd)
        except OSError:
            pass
        if session_identity is not None:
            try:
                current = os.stat(session_name, dir_fd=root_fd, follow_symlinks=False)
                if (current.st_dev, current.st_ino) == session_identity:
                    os.rmdir(session_name, dir_fd=root_fd)
            except OSError:
                pass
    finally:
        if assets_fd is not None:
            try:
                os.close(assets_fd)
            except OSError:
                pass
        try:
            os.close(session_fd)
        except OSError:
            pass


def _cleanup_new_session(root_fd: int, session_name: str, identity: tuple[int, int]) -> None:
    """Remove a just-created empty session only if its identity is unchanged."""

    try:
        info = os.stat(session_name, dir_fd=root_fd, follow_symlinks=False)
        if not stat.S_ISDIR(info.st_mode) or (info.st_dev, info.st_ino) != identity:
            return
        os.rmdir(session_name, dir_fd=root_fd)
    except OSError:
        # A replacement or a non-empty directory is not ours to remove.
        pass


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
    opened_root_info = os.fstat(root_fd)
    if (opened_root_info.st_dev, opened_root_info.st_ino) != validated_root_identity:
        _close_fd(root_fd)
        raise ValidationError("reviews root changed while being opened")
    staging_name: str | None = None
    staging_fd: int | None = None
    staging_identity: tuple[int, int] | None = None
    created_session = False
    session_fd = None
    assets_fd = None
    staged_assets_fd = None
    asset_stats: dict[str, tuple[int, int]] = {}
    review_stat: tuple[int, int] | None = None
    created_session_identity: tuple[int, int] | None = None
    try:
        staging_name, staging_fd, staging_identity = _create_staging(root_fd, review["id"])
        os.mkdir("assets", mode=0o755, dir_fd=staging_fd)
        staged_assets_fd = _open_directory(staging_fd, "assets", "staged assets")
        for group in review["groups"]:
            for item in group["items"]:
                source = sources[item["id"]]
                destination_name = Path(item["image"]).name
                actual_bytes, actual_sha256 = _copy_source(
                    source, staged_assets_fd, destination_name, f"item {item['id']} source"
                )
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
                info = os.stat(destination_name, dir_fd=staged_assets_fd, follow_symlinks=False)
                asset_stats[destination_name] = (info.st_dev, info.st_ino)
        _close_fd(staged_assets_fd)
        staged_assets_fd = None
        _write_owned(staging_fd, "review.json", canonical_json(review))
        staged_review_info = os.stat("review.json", dir_fd=staging_fd, follow_symlinks=False)

        # mkdir is the no-overwrite install point.  In particular, do not use
        # os.rename(staging, session): on POSIX that can replace an empty
        # directory that appeared between the existence check and rename.
        try:
            os.mkdir(review["id"], mode=0o755, dir_fd=root_fd)
        except FileExistsError as exc:
            raise PublishError(f"session appeared during publish: {review['id']}") from exc
        created_session = True
        created_info = os.stat(review["id"], dir_fd=root_fd, follow_symlinks=False)
        if not stat.S_ISDIR(created_info.st_mode):
            raise PublishError(f"new review session is not a directory: {review['id']}")
        created_session_identity = (created_info.st_dev, created_info.st_ino)
        session_fd = _open_directory(root_fd, review["id"], "new review session")
        os.rename("assets", "assets", src_dir_fd=staging_fd, dst_dir_fd=session_fd)
        assets_fd = _open_directory(session_fd, "assets", "new session assets")
        os.rename("review.json", "review.json", src_dir_fd=staging_fd, dst_dir_fd=session_fd)
        installed_review_info = os.stat("review.json", dir_fd=session_fd, follow_symlinks=False)
        if (installed_review_info.st_dev, installed_review_info.st_ino) == (staged_review_info.st_dev, staged_review_info.st_ino):
            review_stat = (installed_review_info.st_dev, installed_review_info.st_ino)
        _cleanup_staging(root_fd, staging_name, staging_fd, staging_identity)
        _close_fd(staging_fd)
        staging_fd = None
        os.close(assets_fd)
        assets_fd = None
        os.close(session_fd)
        session_fd = None
        os.close(root_fd)
        return {
            "schema_version": 1,
            "id": review["id"],
            "session": str(session),
            "review": str(session / "review.json"),
            "assets": len(sources),
        }
    except Exception:
        _close_fd(staged_assets_fd)
        staged_assets_fd = None
        if created_session and session_fd is not None:
            _cleanup_owned_session(
                root_fd,
                review["id"],
                session_fd,
                assets_fd,
                asset_stats,
                review_stat,
                created_session_identity,
            )
            session_fd = None
            assets_fd = None
        elif created_session and created_session_identity is not None:
            _cleanup_new_session(root_fd, review["id"], created_session_identity)
        if staging_fd is not None and staging_name is not None and staging_identity is not None:
            try:
                _cleanup_staging(root_fd, staging_name, staging_fd, staging_identity)
            except OSError:
                pass
            finally:
                _close_fd(staging_fd)
            staging_fd = None
        try:
            os.close(root_fd)
        except OSError:
            pass
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

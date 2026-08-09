#!/usr/bin/env python3
"""Publish a validated image manifest as an immutable visual-review session."""

from __future__ import annotations

import argparse
import os
import stat
import shutil
import sys
import tempfile
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


def _open_directory(parent_fd: int | None, path_or_name: Path | str, where: str) -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = None
    try:
        if parent_fd is None:
            fd = os.open(path_or_name, flags)
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


def _copy_source(source: SourceReference, destination: Path, where: str) -> None:
    """Copy from one already-validated descriptor, never reopening its path."""

    with open_source_reference(source, where) as stream:
        with destination.open("wb") as output:
            while True:
                chunk = stream.read(COPY_CHUNK)
                if not chunk:
                    break
                output.write(chunk)


def _write_owned(path: Path, text: str) -> None:
    # The path is inside a freshly-created, invocation-owned staging directory.
    path.write_text(text, encoding="utf-8", newline="\n")


def _cleanup_owned_session(
    root_fd: int,
    session_name: str,
    session_fd: int,
    assets_fd: int | None,
    asset_stats: dict[str, tuple[int, int]],
    review_stat: tuple[int, int] | None,
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
        try:
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


def publish_session(reviews_root: Path, source_manifest: Path) -> dict[str, Any]:
    """Publish one session and return the canonical machine-readable summary."""

    root = ensure_root(reviews_root)
    require_secure_fs_support()
    manifest_path = source_manifest.absolute()
    review, sources = read_rich_manifest(manifest_path)
    session = root / review["id"]
    if session.exists() or session.is_symlink():
        raise PublishError(f"session already exists: {review['id']}")

    root_fd = _open_directory(None, root, "reviews root")
    staging = Path(tempfile.mkdtemp(prefix=f".{review['id']}.publish-", dir=str(root)))
    created_session = False
    session_fd = None
    assets_fd = None
    asset_stats: dict[str, tuple[int, int]] = {}
    review_stat: tuple[int, int] | None = None
    try:
        staged_assets = staging / "assets"
        staged_assets.mkdir()
        for group in review["groups"]:
            for item in group["items"]:
                source = sources[item["id"]]
                destination = staged_assets / Path(item["image"]).name
                _copy_source(source, destination, f"item {item['id']} source")
                os.chmod(destination, 0o644)
                info = os.stat(destination, follow_symlinks=False)
                asset_stats[destination.name] = (info.st_dev, info.st_ino)
        staged_review = staging / "review.json"
        _write_owned(staged_review, canonical_json(review))
        staged_review_info = os.stat(staged_review, follow_symlinks=False)

        # mkdir is the no-overwrite install point.  In particular, do not use
        # os.rename(staging, session): on POSIX that can replace an empty
        # directory that appeared between the existence check and rename.
        try:
            session.mkdir(mode=0o755)
        except FileExistsError as exc:
            raise PublishError(f"session appeared during publish: {review['id']}") from exc
        created_session = True
        session_fd = _open_directory(root_fd, review["id"], "new review session")
        os.rename(staged_assets, "assets", dst_dir_fd=session_fd)
        assets_fd = _open_directory(session_fd, "assets", "new session assets")
        os.rename(staged_review, "review.json", dst_dir_fd=session_fd)
        installed_review_info = os.stat("review.json", dir_fd=session_fd, follow_symlinks=False)
        if (installed_review_info.st_dev, installed_review_info.st_ino) == (staged_review_info.st_dev, staged_review_info.st_ino):
            review_stat = (installed_review_info.st_dev, installed_review_info.st_ino)
        staging.rmdir()
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
        if created_session and session_fd is not None:
            _cleanup_owned_session(root_fd, review["id"], session_fd, assets_fd, asset_stats, review_stat)
            session_fd = None
            assets_fd = None
        # The staging directory and its contents are always invocation-owned.
        shutil.rmtree(staging, ignore_errors=True)
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

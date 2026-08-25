#!/usr/bin/env python3
"""Small fd-relative no-replace directory publication helpers for experiments."""

from __future__ import annotations

import ctypes
import errno
import os
import secrets
import stat
from pathlib import Path


RENAME_NOREPLACE = 1
MAX_STAGE_ATTEMPTS = 32


class AtomicPublishError(RuntimeError):
    """The platform or target cannot provide the required publication semantics."""


class StageName(str):
    """A staging name carrying the identity captured when it was created."""

    def __new__(
        cls,
        value: str,
        *,
        parent_identity: tuple[int, int],
        stage_identity: tuple[int, int],
    ) -> "StageName":
        result = super().__new__(cls, value)
        result.parent_identity = parent_identity
        result.stage_identity = stage_identity
        return result


def _component(value: str, where: str) -> str:
    if not value or value in {".", ".."} or "/" in value or "\\" in value or "\x00" in value:
        raise AtomicPublishError(f"{where} is not a safe single path component")
    return value


def open_directory_no_symlinks(
    path: Path,
    expected_identity: tuple[int, int] | None = None,
) -> int:
    """Open every component without following symlinks and return the final fd."""
    absolute = path.absolute()
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    current = os.open("/", flags)
    try:
        for component in absolute.parts[1:]:
            _component(component, "directory path component")
            following = os.open(component, flags, dir_fd=current)
            os.close(current)
            current = following
        info = os.fstat(current)
        if not stat.S_ISDIR(info.st_mode):
            raise AtomicPublishError("publication parent is not a directory")
        if expected_identity is not None and (info.st_dev, info.st_ino) != expected_identity:
            raise AtomicPublishError("publication parent changed after validation")
        return current
    except Exception:
        os.close(current)
        raise


def create_stage(parent_fd: int, destination_name: str) -> tuple[str, Path]:
    """Create a private staging directory inside an already-open parent."""
    destination_name = _component(destination_name, "publication destination")
    for _ in range(MAX_STAGE_ATTEMPTS):
        stage_name = f".{destination_name}.stage-{secrets.token_hex(12)}"
        try:
            os.mkdir(stage_name, mode=0o700, dir_fd=parent_fd)
        except FileExistsError:
            continue
        stage_path = Path(f"/proc/self/fd/{parent_fd}") / stage_name
        info = os.stat(stage_name, dir_fd=parent_fd, follow_symlinks=False)
        if not stat.S_ISDIR(info.st_mode):
            raise AtomicPublishError("new staging entry is not a directory")
        parent_info = os.fstat(parent_fd)
        return StageName(
            stage_name,
            parent_identity=(parent_info.st_dev, parent_info.st_ino),
            stage_identity=(info.st_dev, info.st_ino),
        ), stage_path
    raise AtomicPublishError("could not allocate a unique staging directory")


def publish_no_replace(parent_fd: int, stage_name: str, destination_name: str) -> None:
    """Rename within one opened parent without replacing an existing destination."""
    if not isinstance(stage_name, StageName):
        raise AtomicPublishError("publication staging identity is unavailable")
    parent_info = os.fstat(parent_fd)
    if not _same_identity(parent_info, stage_name.parent_identity):
        raise AtomicPublishError("publication parent identity changed")
    try:
        stage_info = os.stat(stage_name, dir_fd=parent_fd, follow_symlinks=False)
    except OSError as exc:
        raise AtomicPublishError("publication staging directory is unavailable") from exc
    if not stat.S_ISDIR(stage_info.st_mode) or not _same_identity(stage_info, stage_name.stage_identity):
        raise AtomicPublishError("publication staging directory changed before install")
    stage_name = _component(stage_name, "staging directory")
    destination_name = _component(destination_name, "publication destination")
    if os.name != "posix":
        raise AtomicPublishError("atomic no-replace directory publication requires Linux/WSL")
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    if renameat2 is None:
        raise AtomicPublishError("Linux/WSL renameat2 no-replace publication is unavailable")
    renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    renameat2.restype = ctypes.c_int
    result = renameat2(
        parent_fd,
        os.fsencode(stage_name),
        parent_fd,
        os.fsencode(destination_name),
        RENAME_NOREPLACE,
    )
    if result != 0:
        error = ctypes.get_errno()
        if error == errno.EEXIST:
            raise FileExistsError(destination_name)
        if error in {errno.EINVAL, errno.ENOSYS, errno.EXDEV, getattr(errno, "EOPNOTSUPP", errno.EINVAL)}:
            raise AtomicPublishError("output parent filesystem does not support atomic Linux no-replace directory publication")
        raise OSError(error, os.strerror(error), destination_name)
    installed = os.stat(destination_name, dir_fd=parent_fd, follow_symlinks=False)
    if not stat.S_ISDIR(installed.st_mode) or not _same_identity(installed, stage_name.stage_identity):
        raise AtomicPublishError("published directory identity does not match the validated staging directory")
    os.fsync(parent_fd)


def _same_identity(left: os.stat_result, right: tuple[int, int]) -> bool:
    return (left.st_dev, left.st_ino) == right


def _remove_tree_contents(directory_fd: int) -> bool:
    """Remove only entries that remain the entries observed in this fd."""
    complete = True
    with os.scandir(f"/proc/self/fd/{directory_fd}") as entries:
        for entry in entries:
            name = _component(entry.name, "staging entry")
            try:
                observed = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            except FileNotFoundError:
                continue
            if stat.S_ISDIR(observed.st_mode):
                flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
                if hasattr(os, "O_CLOEXEC"):
                    flags |= os.O_CLOEXEC
                try:
                    child_fd = os.open(name, flags, dir_fd=directory_fd)
                except OSError:
                    complete = False
                    continue
                try:
                    child_info = os.fstat(child_fd)
                    if not os.path.samestat(observed, child_info) or not _remove_tree_contents(child_fd):
                        complete = False
                        continue
                    current = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                    if not os.path.samestat(child_info, current):
                        complete = False
                        continue
                    os.rmdir(name, dir_fd=directory_fd)
                except (FileNotFoundError, NotADirectoryError, OSError):
                    complete = False
                finally:
                    os.close(child_fd)
                continue
            if not stat.S_ISREG(observed.st_mode):
                # Never remove a symlink or another replacement type during cleanup.
                complete = False
                continue
            current = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            if not os.path.samestat(observed, current):
                complete = False
                continue
            try:
                os.unlink(name, dir_fd=directory_fd)
            except OSError:
                complete = False
    return complete


def cleanup_stage(parent_fd: int, stage_name: str) -> bool:
    """Safely remove a stage still attached to its originally opened parent.

    The name returned by :func:`create_stage` carries both parent and stage
    identities.  A plain string is rejected as unknown rather than being
    treated as permission to remove an arbitrary directory.  Cleanup is
    descriptor-relative and skips a stage whose name has been replaced.
    """
    if not isinstance(stage_name, StageName):
        return False
    try:
        parent_info = os.fstat(parent_fd)
        if not _same_identity(parent_info, stage_name.parent_identity):
            return False
        stage_info = os.stat(stage_name, dir_fd=parent_fd, follow_symlinks=False)
        if not _same_identity(stage_info, stage_name.stage_identity) or not stat.S_ISDIR(stage_info.st_mode):
            return False
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        if hasattr(os, "O_CLOEXEC"):
            flags |= os.O_CLOEXEC
        stage_fd = os.open(stage_name, flags, dir_fd=parent_fd)
        try:
            opened_info = os.fstat(stage_fd)
            if not _same_identity(opened_info, stage_name.stage_identity):
                return False
            if not _remove_tree_contents(stage_fd):
                return False
            current = os.stat(stage_name, dir_fd=parent_fd, follow_symlinks=False)
            if not _same_identity(current, stage_name.stage_identity):
                return False
            os.rmdir(stage_name, dir_fd=parent_fd)
            os.fsync(parent_fd)
            return True
        finally:
            os.close(stage_fd)
    except (FileNotFoundError, NotADirectoryError, OSError):
        return False

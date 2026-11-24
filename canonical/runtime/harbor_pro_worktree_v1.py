"""Bounded, no-follow Pro workspace staging. This is NOT a sandbox.

The caller must create an empty, private destination and discard it after any
error. Tests running in the copy still have the same container authority and
can access the original workspace by absolute path. This module never runs
repository code, applies patches, or grants execution authority.
"""
from __future__ import annotations

import os
from pathlib import Path
import stat
from typing import Any

MAX_ENTRIES = 50_000
MAX_DEPTH = 32
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_TOTAL_BYTES = 512 * 1024 * 1024
SKIPPED_DIRS = frozenset({'.git', '.hg', '.svn', '__pycache__', '.pytest_cache',
                          '.mypy_cache', '.ruff_cache', '.tox', '.venv', 'venv'})


class StageError(ValueError):
    pass


def _identity(st: os.stat_result) -> tuple[int, int, int, int, int, int, int]:
    return (st.st_dev, st.st_ino, st.st_mode, st.st_nlink, st.st_size,
            st.st_mtime_ns, st.st_ctime_ns)


def _write_all(fd: int, data: bytes) -> None:
    view = memoryview(data)
    while view:
        n = os.write(fd, view)
        if n <= 0:
            raise StageError('DESTINATION_WRITE_FAILED')
        view = view[n:]


def stage_worktree(source: str | Path, destination: str | Path) -> dict[str, Any]:
    """Copy a bounded snapshot, omitting symlinks and VCS/cache directories.

    Paths are opened component-by-component without following symlinks below
    the opened source and destination roots. Never call this concurrently with
    untrusted writers and never treat success as proof that a later test is
    confined. Resource limits and skipped entries are explicitly reported.
    """
    src, dst = Path(source), Path(destination)
    if not src.is_absolute() or not dst.is_absolute():
        raise StageError('ABSOLUTE_PATHS_REQUIRED')
    try:
        src_real, dst_real = src.resolve(strict=True), dst.resolve(strict=True)
        if (src_real == dst_real or src_real in dst_real.parents or dst_real in src_real.parents
                or src_real == Path('/') or dst_real == Path('/')):
            raise StageError('OVERLAPPING_OR_ROOT_PATH')
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        srcfd = os.open(src, flags)
        try:
            dstfd = os.open(dst, flags)
        except BaseException:
            os.close(srcfd)
            raise
    except OSError as exc:
        raise StageError('ROOT_UNAVAILABLE_OR_SYMLINK') from exc
    entries = files = total = skipped = excluded = 0
    skipped_examples: list[str] = []
    try:
        with os.scandir(dstfd) as it:
            if next(it, None) is not None:
                raise StageError('DESTINATION_NOT_EMPTY')
        dst_st = os.fstat(dstfd)
        if dst_st.st_uid != os.geteuid() or dst_st.st_mode & 0o077:
            raise StageError('DESTINATION_NOT_PRIVATE')

        def walk(sfd: int, dfd: int, prefix: str, depth: int) -> None:
            nonlocal entries, files, total, skipped, excluded
            if depth > MAX_DEPTH:
                raise StageError('DEPTH_LIMIT')
            names: list[str] = []
            with os.scandir(sfd) as it:
                for item in it:
                    entries += 1
                    if entries > MAX_ENTRIES:
                        raise StageError('ENTRY_LIMIT')
                    names.append(item.name)
            for name in sorted(names):
                rel = prefix + '/' + name if prefix else name
                if name in SKIPPED_DIRS:
                    excluded += 1
                    continue
                before = os.stat(name, dir_fd=sfd, follow_symlinks=False)
                if stat.S_ISLNK(before.st_mode):
                    skipped += 1
                    if len(skipped_examples) < 20:
                        skipped_examples.append(rel)
                    continue
                if stat.S_ISDIR(before.st_mode):
                    child = os.open(name, flags, dir_fd=sfd)
                    try:
                        if _identity(os.fstat(child)) != _identity(before):
                            raise StageError('SOURCE_CHANGED')
                        os.mkdir(name, 0o700, dir_fd=dfd)
                        dest = os.open(name, flags, dir_fd=dfd)
                        try:
                            walk(child, dest, rel, depth + 1)
                            named_after = os.stat(name, dir_fd=sfd, follow_symlinks=False)
                            if _identity(os.fstat(child)) != _identity(before) or _identity(named_after) != _identity(before):
                                raise StageError('SOURCE_CHANGED')
                            os.fchmod(dest, stat.S_IMODE(before.st_mode) & 0o777)
                        finally:
                            os.close(dest)
                    finally:
                        os.close(child)
                elif stat.S_ISREG(before.st_mode):
                    if before.st_nlink != 1:
                        raise StageError('SOURCE_HARDLINK_REJECTED')
                    if before.st_size > MAX_FILE_BYTES or total + before.st_size > MAX_TOTAL_BYTES:
                        raise StageError('BYTE_LIMIT')
                    source_file = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=sfd)
                    try:
                        if _identity(os.fstat(source_file)) != _identity(before):
                            raise StageError('SOURCE_CHANGED')
                        output = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                         0o600, dir_fd=dfd)
                        try:
                            read = 0
                            while True:
                                data = os.read(source_file, 65536)
                                if not data:
                                    break
                                read += len(data)
                                if read > before.st_size:
                                    raise StageError('SOURCE_CHANGED')
                                _write_all(output, data)
                            after = os.fstat(source_file)
                            named_after = os.stat(name, dir_fd=sfd, follow_symlinks=False)
                            if read != before.st_size or _identity(after) != _identity(before) or _identity(named_after) != _identity(before):
                                raise StageError('SOURCE_CHANGED')
                            os.fchmod(output, stat.S_IMODE(before.st_mode) & 0o777)
                        finally:
                            os.close(output)
                    finally:
                        os.close(source_file)
                    total += read
                    files += 1
                else:
                    raise StageError('SPECIAL_FILE_REJECTED')

        root_before = os.fstat(srcfd)
        walk(srcfd, dstfd, '', 0)
        if _identity(os.fstat(srcfd)) != _identity(root_before):
            raise StageError('SOURCE_CHANGED')
        return {'status': 'STAGED__UNVERIFIED', 'files': files, 'bytes': total,
                'entries_seen': entries, 'symlinks_skipped': skipped, 'excluded_entries': excluded,
                'skipped_symlink_examples': skipped_examples,
                'dependency_completeness_verified': False, 'confinement_verified': False,
                'test_execution_authorized': False, 'patch_applied': False}
    except OSError as exc:
        raise StageError('STAGING_IO_ERROR') from exc
    finally:
        os.close(dstfd)
        os.close(srcfd)

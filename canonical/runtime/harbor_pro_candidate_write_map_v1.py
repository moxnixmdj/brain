"""All-or-nothing regular-file application of imported-engine winner maps.

Input source maps were produced by code already running inside the disposable
task container. This helper validates repository-relative regular paths and
restores the previous bytes if a later write fails. It does not run code,
claim confinement, or invoke a verifier.
"""
from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
import os
import stat
from typing import Any

MAX_FILES = 500
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_TOTAL_BYTES = 256 * 1024 * 1024
MAX_PATH_BYTES = 1024


class CandidateApplyError(ValueError):
    pass


def _rel_parts(raw: Any) -> tuple[str, tuple[str, ...]]:
    if not isinstance(raw, str):
        raise CandidateApplyError('PATH_NOT_STRING')
    value = raw.replace('\\', '/')
    while value.startswith('./'):
        value = value[2:]
    if not value or value.startswith('/') or '\x00' in value or len(value.encode('utf-8')) > MAX_PATH_BYTES:
        raise CandidateApplyError('PATH_INVALID')
    path = PurePosixPath(value)
    parts = path.parts
    if not parts or any(part in ('', '.', '..') for part in parts):
        raise CandidateApplyError('PATH_INVALID')
    if parts[0].lower() in {'.git', '.hg', '.svn'}:
        raise CandidateApplyError('VCS_PATH_REJECTED')
    return value, parts


def source_map_from_winner(winner: Any) -> tuple[dict[str, str], int, bool]:
    """Extract a bounded source map and the engine's reported diff byte size."""
    if not isinstance(winner, dict):
        return {}, 0, False
    out: dict[str, str] = {}

    def add(path: Any, source: Any) -> None:
        rel, _ = _rel_parts(path)
        if not isinstance(source, str):
            raise CandidateApplyError('SOURCE_NOT_STRING')
        if len(source.encode('utf-8')) > MAX_FILE_BYTES:
            raise CandidateApplyError('SOURCE_TOO_LARGE')
        if rel in out and out[rel] != source:
            raise CandidateApplyError('CONFLICTING_SOURCE_MAP')
        out[rel] = source

    patched_files = winner.get('patched_files')
    if isinstance(patched_files, dict):
        for path, source in patched_files.items():
            add(path, source)
    file_name = winner.get('file')
    patched_source = winner.get('patched_source')
    if file_name is not None or patched_source is not None:
        if not isinstance(file_name, str) or not isinstance(patched_source, str):
            raise CandidateApplyError('WINNER_SOURCE_INCOMPLETE')
        add(file_name, patched_source)
    extra = winner.get('extra_patches')
    if isinstance(extra, dict):
        for path, source in extra.items():
            add(path, source)
    if len(out) > MAX_FILES:
        raise CandidateApplyError('FILE_COUNT_LIMIT')
    total = sum(len(value.encode('utf-8')) for value in out.values())
    if total > MAX_TOTAL_BYTES:
        raise CandidateApplyError('SOURCE_MAP_TOO_LARGE')
    diff = winner.get('diff')
    diff_bytes = len(diff.encode('utf-8')) if isinstance(diff, str) else 0
    return out, diff_bytes, bool(out)


def _open_root(repo: str | Path) -> tuple[Path, int]:
    path = Path(repo)
    if not path.is_absolute():
        raise CandidateApplyError('ABSOLUTE_REPOSITORY_REQUIRED')
    try:
        resolved = path.resolve(strict=True)
        fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except OSError as exc:
        raise CandidateApplyError('REPOSITORY_UNAVAILABLE') from exc
    if resolved == Path('/'):
        os.close(fd)
        raise CandidateApplyError('ROOT_REPOSITORY_REJECTED')
    return resolved, fd


def _open_parent(root_fd: int, parts: tuple[str, ...], *, create: bool) -> int:
    fd = os.dup(root_fd)
    try:
        for part in parts:
            child = None
            try:
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            except FileNotFoundError:
                if not create:
                    raise CandidateApplyError('PARENT_MISSING')
                os.mkdir(part, 0o755, dir_fd=fd)
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            except OSError as exc:
                raise CandidateApplyError('PARENT_UNSAFE_OR_UNREADABLE') from exc
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def _read_old(root_fd: int, parts: tuple[str, ...]) -> tuple[bytes | None, int | None, int | None]:
    try:
        parent = _open_parent(root_fd, parts[:-1], create=False)
    except CandidateApplyError as exc:
        if str(exc) == 'PARENT_MISSING':
            return None, None, None
        raise
    try:
        try:
            st = os.stat(parts[-1], dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            return None, None, None
        if not stat.S_ISREG(st.st_mode):
            raise CandidateApplyError('TARGET_NOT_REGULAR_FILE')
        if st.st_size > MAX_FILE_BYTES:
            raise CandidateApplyError('OLD_FILE_TOO_LARGE')
        try:
            fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        except OSError as exc:
            raise CandidateApplyError('TARGET_UNSAFE') from exc
        try:
            chunks = []
            remaining = st.st_size + 1
            while remaining:
                chunk = os.read(fd, min(65536, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            data = b''.join(chunks)
            after = os.fstat(fd)
            named = os.stat(parts[-1], dir_fd=parent, follow_symlinks=False)
            if len(data) != st.st_size or (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) != (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns) or (named.st_dev, named.st_ino, named.st_size) != (st.st_dev, st.st_ino, st.st_size):
                raise CandidateApplyError('TARGET_CHANGED')
        finally:
            os.close(fd)
        return data, stat.S_IMODE(st.st_mode), len(data)
    finally:
        os.close(parent)


def _write_one(root_fd: int, parts: tuple[str, ...], data: bytes, old_mode: int | None) -> None:
    parent = _open_parent(root_fd, parts[:-1], create=True)
    try:
        try:
            current = os.stat(parts[-1], dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            current = None
        if current is not None and not stat.S_ISREG(current.st_mode):
            raise CandidateApplyError('TARGET_NOT_REGULAR_FILE')
        mode = 0o600 if current is None else (old_mode if old_mode is not None else 0o600)
        try:
            fd = os.open(parts[-1], os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, mode, dir_fd=parent)
        except OSError as exc:
            raise CandidateApplyError('TARGET_WRITE_REFUSED') from exc
        try:
            view = memoryview(data)
            while view:
                n = os.write(fd, view)
                if n <= 0:
                    raise CandidateApplyError('TARGET_WRITE_FAILED')
                view = view[n:]
            os.fchmod(fd, mode & 0o777)
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        os.close(parent)


def apply_source_map(repo: str | Path, source_map: dict[str, str]) -> dict[str, Any]:
    """Apply a validated source map, restoring prior bytes on any failure."""
    resolved, root_fd = _open_root(repo)
    old: list[tuple[str, tuple[str, ...], bytes | None, int | None]] = []
    encoded: dict[str, bytes] = {}
    total_new = 0
    total_old = 0
    try:
        if not isinstance(source_map, dict) or not source_map or len(source_map) > MAX_FILES:
            raise CandidateApplyError('SOURCE_MAP_EMPTY_OR_TOO_LARGE')
        for raw_path, source in sorted(source_map.items()):
            original, parts = _rel_parts(raw_path)
            if not isinstance(source, str):
                raise CandidateApplyError('SOURCE_NOT_STRING')
            data = source.encode('utf-8')
            if len(data) > MAX_FILE_BYTES or total_new + len(data) > MAX_TOTAL_BYTES:
                raise CandidateApplyError('SOURCE_MAP_TOO_LARGE')
            previous, mode, old_size = _read_old(root_fd, parts)
            if previous is not None and total_old + (old_size or 0) > MAX_TOTAL_BYTES:
                raise CandidateApplyError('ROLLBACK_DATA_TOO_LARGE')
            total_new += len(data)
            total_old += old_size or 0
            encoded[original] = data
            old.append((original, parts, previous, mode))
        applied: list[str] = []
        for rel, parts, previous, mode in old:
            _write_one(root_fd, parts, encoded[rel], mode)
            applied.append(rel)
        return {'status': 'APPLIED__UNVERIFIED', 'repository': str(resolved),
                'applied_paths': applied, 'files_written': len(applied),
                'new_bytes': total_new, 'old_bytes_backed_up': total_old,
                'rollback_verified': False, 'official_verifier_invoked': False}
    except BaseException as exc:
        rollback_errors: list[str] = []
        for rel, parts, previous, mode in reversed(old):
            try:
                if previous is None:
                    parent = _open_parent(root_fd, parts[:-1], create=False)
                    try:
                        try:
                            os.unlink(parts[-1], dir_fd=parent)
                        except FileNotFoundError:
                            pass
                    finally:
                        os.close(parent)
                else:
                    _write_one(root_fd, parts, previous, mode)
            except Exception as rb_exc:
                rollback_errors.append(type(rb_exc).__name__ + ':' + str(rb_exc)[:80])
        detail = type(exc).__name__ + ':' + str(exc)[:160]
        if rollback_errors:
            detail += ';rollback_errors=' + ','.join(rollback_errors[:5])
        raise CandidateApplyError(detail) from exc
    finally:
        os.close(root_fd)

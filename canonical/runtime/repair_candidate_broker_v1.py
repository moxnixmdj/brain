"""Unadmitted, read-only staging and comparison for a single repair candidate.

This module can copy a selected tree into a fresh staging directory, but it
runs no code, publishes no files to the source, grants no capability, and does
not verify semantic correctness. It snapshots a *trusted, quiescent* tree,
compares another quiescent tree, and forms an unsigned request for the existing
effect broker. Never let an unconfined worker access the source or run untrusted
code based on this module. Snapshot hashes are content bindings, not
attestations or security boundaries.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import tempfile
import shutil

from canonical.runtime.effect_broker_contract_v1 import make_request

MAX_FILES = 512
MAX_DIRS = 512
MAX_FILE_BYTES = 2_000_000
MAX_TOTAL_BYTES = 16_000_000
MAX_DEPTH = 32
MAX_PATH_BYTES = 1024
SCHEMA = 'BRAIN_REPAIR_CANDIDATE_BROKER_V1'


class CandidateDenied(ValueError):
    pass


@dataclass(frozen=True)
class ProjectSnapshot:
    # Immutable bytes held by the parent; not an identity or proof of origin.
    directories: tuple[str, ...]
    files: tuple[tuple[str, bytes], ...]
    digest: str
    # Used only to prevent accidentally staging inside the source tree. This is
    # caller-visible metadata, not a trusted attestation of snapshot origin.
    origin: str


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _identity(st: os.stat_result) -> tuple:
    return (st.st_dev, st.st_ino, st.st_mode, st.st_size,
            st.st_mtime_ns, st.st_ctime_ns, st.st_nlink)


def _relative(raw: str) -> str:
    if not isinstance(raw, str) or not raw or '\x00' in raw or '\\' in raw:
        raise CandidateDenied('PATH_INVALID')
    try:
        if len(raw.encode('utf-8')) > MAX_PATH_BYTES:
            raise CandidateDenied('PATH_TOO_LONG')
    except UnicodeError as exc:
        raise CandidateDenied('PATH_INVALID') from exc
    path = PurePosixPath(raw)
    if (path.is_absolute() or any(p in ('', '.', '..', '.git') for p in raw.split('/'))
            or str(path) != raw or len(path.parts) > MAX_DEPTH):
        raise CandidateDenied('PATH_INVALID')
    return raw


def _digest(directories: tuple[str, ...], files: tuple[tuple[str, bytes], ...]) -> str:
    content = {'directories': directories,
               'files': [(path, len(data), _sha(data)) for path, data in files]}
    return _sha(json.dumps(content, sort_keys=True, separators=(',', ':'),
                           ensure_ascii=False).encode('utf-8'))


def snapshot_project(root: str | Path) -> ProjectSnapshot:
    """Capture a bounded tree without following symlinks or opening special files.

    The caller must select the complete intended project and keep it quiescent
    while taking the snapshot. Parent path components and concurrent rename or
    privileged filesystem attacks are not a security boundary. No secrets are
    automatically redacted. Both the original and staged tree must be quiescent.
    """
    if not all(hasattr(os, name) for name in ('O_NOFOLLOW', 'O_DIRECTORY', 'O_NONBLOCK')):
        raise CandidateDenied('REQUIRED_NOFOLLOW_FLAGS_UNAVAILABLE')
    if not isinstance(root, (str, Path)) or not os.fspath(root) or '\x00' in os.fspath(root):
        raise CandidateDenied('PROJECT_ROOT_INVALID')
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK
    files: list[tuple[str, bytes]] = []
    dirs: list[str] = []
    total = 0

    def walk(fd: int, prefix: str) -> None:
        nonlocal total
        before = os.fstat(fd)
        if not stat.S_ISDIR(before.st_mode):
            raise CandidateDenied('DIRECTORY_REQUIRED')
        names = []
        with os.scandir(fd) as stream:
            for entry in stream:
                if len(names) >= MAX_FILES + MAX_DIRS:
                    raise CandidateDenied('TOO_MANY_DIRECTORY_ENTRIES')
                names.append(entry.name)
        for name in sorted(names):
            rel = _relative(prefix + '/' + name if prefix else name)
            st = os.stat(name, dir_fd=fd, follow_symlinks=False)
            if stat.S_ISDIR(st.st_mode):
                if len(dirs) >= MAX_DIRS:
                    raise CandidateDenied('TOO_MANY_DIRECTORIES')
                child = os.open(name, flags, dir_fd=fd)
                try:
                    if _identity(st) != _identity(os.fstat(child)):
                        raise CandidateDenied('TREE_CHANGED_DURING_SNAPSHOT')
                    dirs.append(rel)
                    walk(child, rel)
                    if _identity(os.stat(name, dir_fd=fd, follow_symlinks=False)) != _identity(os.fstat(child)):
                        raise CandidateDenied('TREE_CHANGED_DURING_SNAPSHOT')
                finally:
                    os.close(child)
            elif stat.S_ISREG(st.st_mode):
                if st.st_nlink != 1:
                    raise CandidateDenied('HARDLINK_DENIED')
                if len(files) >= MAX_FILES:
                    raise CandidateDenied('TOO_MANY_FILES')
                if st.st_size > MAX_FILE_BYTES or total + st.st_size > MAX_TOTAL_BYTES:
                    raise CandidateDenied('PROJECT_BYTES_EXCEEDED')
                child = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
                try:
                    opened = os.fstat(child)
                    if not stat.S_ISREG(opened.st_mode) or _identity(st) != _identity(opened):
                        raise CandidateDenied('TREE_CHANGED_DURING_SNAPSHOT')
                    data = bytearray()
                    while len(data) <= MAX_FILE_BYTES:
                        block = os.read(child, min(65536, MAX_FILE_BYTES + 1 - len(data)))
                        if not block:
                            break
                        data.extend(block)
                    if len(data) > MAX_FILE_BYTES:
                        raise CandidateDenied('PROJECT_BYTES_EXCEEDED')
                    if (_identity(os.fstat(child)) != _identity(opened)
                            or _identity(os.stat(name, dir_fd=fd, follow_symlinks=False)) != _identity(opened)
                            or len(data) != opened.st_size):
                        raise CandidateDenied('TREE_CHANGED_DURING_SNAPSHOT')
                    total += len(data)
                    files.append((rel, bytes(data)))
                finally:
                    os.close(child)
            else:
                raise CandidateDenied('SYMLINK_OR_SPECIAL_FILE_DENIED')
        if _identity(os.fstat(fd)) != _identity(before):
            raise CandidateDenied('TREE_CHANGED_DURING_SNAPSHOT')

    try:
        fd = os.open(os.fspath(root), flags)
        try:
            walk(fd, '')
        finally:
            os.close(fd)
    except CandidateDenied:
        raise
    except (OSError, ValueError, TypeError) as exc:
        raise CandidateDenied('PROJECT_SNAPSHOT_FAILED:' + type(exc).__name__) from exc
    directories = tuple(sorted(dirs))
    captured = tuple(sorted(files))
    return ProjectSnapshot(directories, captured, _digest(directories, captured), os.path.realpath(root))


def _check_snapshot(snapshot: ProjectSnapshot) -> dict[str, bytes]:
    if not isinstance(snapshot, ProjectSnapshot):
        raise CandidateDenied('SNAPSHOT_INVALID')
    try:
        if (not isinstance(snapshot.directories, tuple) or not isinstance(snapshot.files, tuple)
                or not isinstance(snapshot.origin, str) or not os.path.isabs(snapshot.origin)
                or '\x00' in snapshot.origin
                or len(snapshot.files) > MAX_FILES or len(snapshot.directories) > MAX_DIRS
                or snapshot.directories != tuple(sorted(set(snapshot.directories)))):
            raise CandidateDenied('SNAPSHOT_INVALID')
        for path in snapshot.directories:
            _relative(path)
        result = {}
        total = 0
        for path, data in snapshot.files:
            _relative(path)
            if path in result or not isinstance(data, bytes) or len(data) > MAX_FILE_BYTES:
                raise CandidateDenied('SNAPSHOT_INVALID')
            total += len(data)
            if total > MAX_TOTAL_BYTES:
                raise CandidateDenied('SNAPSHOT_INVALID')
            result[path] = data
        directory_set = set(snapshot.directories)
        if directory_set.intersection(result):
            raise CandidateDenied('SNAPSHOT_INVALID')
        for path in (*snapshot.directories, *result):
            parent = PurePosixPath(path).parent.as_posix()
            if parent != '.' and parent not in directory_set:
                raise CandidateDenied('SNAPSHOT_INVALID')
        if snapshot.files != tuple(sorted(snapshot.files)) or snapshot.digest != _digest(snapshot.directories, snapshot.files):
            raise CandidateDenied('SNAPSHOT_INVALID')
        return result
    except (TypeError, ValueError, UnicodeError) as exc:
        if isinstance(exc, CandidateDenied):
            raise
        raise CandidateDenied('SNAPSHOT_INVALID') from exc


def stage_project(snapshot: ProjectSnapshot, *, staging_parent: str | Path) -> Path:
    """Make a new private copy in a trusted parent; no worker is launched.

    The caller owns cleanup and must not run a worker until an independently
    qualified carrier exists. This is not a filesystem sandbox. File metadata,
    executability, symlinks and hard links are deliberately not reproduced.
    """
    files = _check_snapshot(snapshot)
    try:
        parent = Path(staging_parent).resolve(strict=True)
        source = Path(snapshot.origin).resolve(strict=True)
        if not parent.is_dir() or parent == source or source in parent.parents:
            raise CandidateDenied('STAGING_PARENT_INSIDE_SOURCE_OR_INVALID')
        stage = Path(tempfile.mkdtemp(prefix='brain-repair-stage-', dir=parent))
        opened: dict[str, int] = {}
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK
        try:
            opened[''] = os.open(stage, flags)
            for rel in snapshot.directories:
                path = PurePosixPath(rel)
                parent_key = '' if path.parent.as_posix() == '.' else path.parent.as_posix()
                os.mkdir(path.name, 0o700, dir_fd=opened[parent_key])
                opened[rel] = os.open(path.name, flags, dir_fd=opened[parent_key])
            for rel, data in files.items():
                path = PurePosixPath(rel)
                parent_key = '' if path.parent.as_posix() == '.' else path.parent.as_posix()
                fd = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             0o600, dir_fd=opened[parent_key])
                try:
                    view = memoryview(data)
                    while view:
                        count = os.write(fd, view)
                        if count <= 0:
                            raise OSError('STAGE_WRITE_DID_NOT_PROGRESS')
                        view = view[count:]
                finally:
                    os.close(fd)
        except BaseException:
            # No worker has been started. Cleanup assumes the stated trusted,
            # exclusive staging parent; it is not adversarial race protection.
            shutil.rmtree(stage, ignore_errors=True)
            raise
        finally:
            for fd in opened.values():
                os.close(fd)
        return stage
    except CandidateDenied:
        raise
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise CandidateDenied('STAGING_FAILED:' + type(exc).__name__) from exc


def compare_candidate(before: ProjectSnapshot, after: ProjectSnapshot, *, target: str,
                      protected_tests: tuple[str, ...]) -> dict:
    """Assess file scope and content identity only; the result is NOT approval."""
    target = _relative(target)
    if not target.endswith('.py') or not isinstance(protected_tests, tuple) or not protected_tests:
        raise CandidateDenied('REPAIR_SCOPE_INVALID')
    for path in protected_tests:
        _relative(path)
    original, proposed = _check_snapshot(before), _check_snapshot(after)
    if len(set(protected_tests)) != len(protected_tests) or target in protected_tests:
        raise CandidateDenied('REPAIR_SCOPE_INVALID')
    if target not in original or any(path not in original for path in protected_tests):
        raise CandidateDenied('SCOPE_FILE_MISSING')
    if before.directories != after.directories or set(original) != set(proposed):
        raise CandidateDenied('PROJECT_LAYOUT_CHANGED')
    changed = [path for path in original if original[path] != proposed[path]]
    if changed != [target]:
        raise CandidateDenied('ONLY_ONE_TARGET_MAY_CHANGE')
    # Do not import, parse or execute worker-supplied code in the parent. An
    # independent acceptance mechanism must assess its syntax and behavior.
    return {'schema': SCHEMA, 'status': 'CANDIDATE_ONLY__NOT_VERIFIED_OR_AUTHORIZED',
            'target': target, 'protected_tests': list(protected_tests),
            'before_project_sha256': before.digest, 'after_project_sha256': after.digest,
            'expected_pre_sha256': _sha(original[target]), 'candidate_sha256': _sha(proposed[target]),
            'candidate_bytes': len(proposed[target]), 'metadata_checked': False,
            'semantic_acceptance_complete': False,
            'execution_authority': False, 'publication_authority': False}


def acceptance_subject(before: ProjectSnapshot, after: ProjectSnapshot, *, target: str,
                       protected_tests: tuple[str, ...], task_id: str, goal: str,
                       learning_mode: str) -> dict:
    """Bind a requested outcome and test bytes to a candidate, without accepting it.

    Caller-supplied goals and test designations are claims, not trusted evidence.
    The learning mode is a requested policy, not proof it was enforced.
    """
    def token(value: str, label: str, limit: int) -> str:
        if not isinstance(value, str) or not value.strip() or '\x00' in value:
            raise CandidateDenied(label + '_INVALID')
        try:
            if len(value.encode('utf-8')) > limit:
                raise CandidateDenied(label + '_TOO_LONG')
        except UnicodeError as exc:
            raise CandidateDenied(label + '_INVALID') from exc
        return value

    task_id = token(task_id, 'TASK_ID', 256)
    goal = token(goal, 'GOAL', 4096)
    if learning_mode not in ('use', 'off'):
        raise CandidateDenied('LEARNING_MODE_INVALID')
    candidate = compare_candidate(before, after, target=target, protected_tests=protected_tests)
    original = _check_snapshot(before)
    core = {'schema': 'BRAIN_REPAIR_ACCEPTANCE_SUBJECT_V1', 'task_id': task_id,
            'requested_goal': goal, 'requested_learning_mode': learning_mode,
            'candidate': candidate,
            'declared_test_sha256': {path: _sha(original[path]) for path in sorted(protected_tests)}}
    canonical = json.dumps(core, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    return {**core, 'subject_sha256': _sha(canonical),
            'semantic_acceptance_complete': False, 'publication_authority': False}


def acceptance_effect_request(before: ProjectSnapshot, after: ProjectSnapshot, *, target: str,
                              protected_tests: tuple[str, ...], task_id: str, goal: str,
                              learning_mode: str, mission_id: str,
                              capsule_head_sha256: str, action_ref: str) -> dict:
    """Create an unsigned effect request bound to the entire acceptance subject."""
    subject = acceptance_subject(before, after, target=target, protected_tests=protected_tests,
                                 task_id=task_id, goal=goal, learning_mode=learning_mode)
    return make_request(mission_id=mission_id, capsule_head_sha256=capsule_head_sha256,
                        action_ref=action_ref, effect_kind='REPO_WRITE',
                        resource='project:' + subject['candidate']['target'],
                        operation='replace', payload=subject)


def effect_request(before: ProjectSnapshot, after: ProjectSnapshot, *, target: str,
                   protected_tests: tuple[str, ...], mission_id: str,
                   capsule_head_sha256: str, action_ref: str) -> dict:
    """Bind a candidate to the existing unsigned effect-request format.

    This only constructs a request. The final authorizer, an independent
    acceptance gate and an atomic race-safe carrier remain mandatory.
    """
    candidate = compare_candidate(before, after, target=target, protected_tests=protected_tests)
    return make_request(mission_id=mission_id, capsule_head_sha256=capsule_head_sha256,
                        action_ref=action_ref, effect_kind='REPO_WRITE',
                        resource='project:' + candidate['target'], operation='replace',
                        payload=candidate)

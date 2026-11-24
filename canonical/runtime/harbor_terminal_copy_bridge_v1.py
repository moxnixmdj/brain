#!/usr/bin/env python3
"""Narrow deterministic Harbor terminal proposal, not a general task solver.

Only an exact instruction to copy the contents of one existing regular file to
one *new* file beneath the current working directory is understood. Paths are
traversed with directory descriptors and no-follow flags, sizes are bounded,
and no shell text from the instruction is executed. The postcondition is a
local observation, not independent verification or proof of isolation.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shlex
import stat
import sys
from typing import Any

WORKER = '/opt/brain-ro/canonical/runtime/harbor_terminal_copy_bridge_v1.py'
MAX_BYTES = 1_000_000
MAX_REQUEST = 16_000
_NAME = r'[A-Za-z0-9_][A-Za-z0-9_.-]*(?:/[A-Za-z0-9_][A-Za-z0-9_.-]*)*'
_GOAL = re.compile(r'Copy the contents of `(' + _NAME + r')` to a new file `(' + _NAME + r')`\.\Z')


class CopyBridgeError(ValueError):
    pass


def _parts(path: Any) -> list[str]:
    if not isinstance(path, str) or len(path) > 1024 or not re.fullmatch(_NAME, path):
        raise CopyBridgeError('PATH_INVALID')
    parts = path.split('/')
    if len(parts) > 16 or any(part in ('.', '..') for part in parts):
        raise CopyBridgeError('PATH_INVALID')
    return parts


def _root(path: str) -> int:
    if not isinstance(path, str) or not os.path.isabs(path) or path == '/' or path != os.getcwd():
        raise CopyBridgeError('WORKSPACE_INVALID')
    return os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)


def _parent(root: int, path: str) -> tuple[int, str]:
    parts = _parts(path)
    fd = os.dup(root)
    try:
        for part in parts[:-1]:
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        return fd, parts[-1]
    except BaseException:
        os.close(fd)
        raise


def _read(root: int, path: str) -> bytes:
    parent, name = _parent(root, path)
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
                raise CopyBridgeError('SOURCE_NOT_BOUNDED_REGULAR_FILE')
            data = bytearray()
            while len(data) <= MAX_BYTES:
                chunk = os.read(fd, min(65536, MAX_BYTES + 1 - len(data)))
                if not chunk:
                    break
                data.extend(chunk)
            if len(data) > MAX_BYTES:
                raise CopyBridgeError('FILE_TOO_LARGE')
            return bytes(data)
        finally:
            os.close(fd)
    finally:
        os.close(parent)


def _absent(root: int, path: str) -> bool:
    parent, name = _parent(root, path)
    try:
        try:
            os.stat(name, dir_fd=parent, follow_symlinks=False)
            return False
        except FileNotFoundError:
            return True
    finally:
        os.close(parent)


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _command(payload: dict[str, str]) -> str:
    data = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('ascii')
    token = base64.b64encode(data).decode('ascii')
    return ('env -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/tmp python3 -I -B '
            + WORKER + ' copy ' + shlex.quote(token))


def propose(instruction: str, observations: Any, workspace: str) -> dict[str, Any] | None:
    """Return a proposal for the exact supported grammar, or None if unrecognized."""
    match = _GOAL.fullmatch(instruction.strip()) if isinstance(instruction, str) else None
    if not match:
        return None
    fail = {'pass': False, 'status': 'FAIL_CLOSED', 'reason': 'COPY_GROUNDING_OR_POSTCONDITION_FAILED'}
    try:
        src, dst = match.groups()
        if src == dst or not isinstance(observations, list) or len(observations) > 1:
            return fail
        fd = _root(workspace)
        try:
            original = _read(fd, src)
            payload = {'workspace': workspace, 'source': src, 'destination': dst,
                       'source_sha256': _digest(original)}
            command = _command(payload)
            if not observations:
                if not _absent(fd, dst):
                    return fail
                return {'pass': True, 'status': 'COPY_ACTION_PROPOSED__UNVERIFIED',
                        'actions': [{'type': 'terminal_exec', 'args': {'command': command, 'timeout_sec': 30}}]}
            obs = observations[0]
            if (not isinstance(obs, dict) or obs.get('type') != 'terminal_exec'
                    or obs.get('command') != command or type(obs.get('returncode')) is not int
                    or obs['returncode'] != 0 or _read(fd, dst) != original):
                return fail
            return {'pass': True, 'status': 'COPY_LOCAL_POSTCONDITION_OBSERVED__UNVERIFIED',
                    'actions': [{'type': 'finish', 'args': {'summary': 'File contents copied; external verifier decides.'}}]}
        finally:
            os.close(fd)
    except (OSError, CopyBridgeError, ValueError, UnicodeError):
        return fail


def copy(payload: Any) -> None:
    if not isinstance(payload, dict) or set(payload) != {'workspace', 'source', 'destination', 'source_sha256'}:
        raise CopyBridgeError('PAYLOAD_INVALID')
    src, dst, digest = payload['source'], payload['destination'], payload['source_sha256']
    _parts(src)
    _parts(dst)
    if src == dst or not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest):
        raise CopyBridgeError('PAYLOAD_INVALID')
    root = _root(payload['workspace'])
    try:
        data = _read(root, src)
        if _digest(data) != digest:
            raise CopyBridgeError('SOURCE_CHANGED')
        parent, name = _parent(root, dst)
        try:
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o666, dir_fd=parent)
            try:
                view = memoryview(data)
                while view:
                    written = os.write(fd, view)
                    if written <= 0:
                        raise CopyBridgeError('WRITE_FAILED')
                    view = view[written:]
            finally:
                os.close(fd)
        finally:
            os.close(parent)
    finally:
        os.close(root)


def main() -> int:
    try:
        if len(sys.argv) != 3 or sys.argv[1] != 'copy' or len(sys.argv[2]) > MAX_REQUEST:
            raise CopyBridgeError('REQUEST_INVALID')
        raw = base64.b64decode(sys.argv[2], validate=True)
        if len(raw) > MAX_REQUEST:
            raise CopyBridgeError('REQUEST_INVALID')
        copy(json.loads(raw))
        print('COPY_EXECUTED__LOCAL_POSTCONDITION_PENDING')
        return 0
    except (OSError, ValueError, TypeError, UnicodeError) as exc:
        print('COPY_FAILED:' + type(exc).__name__, file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

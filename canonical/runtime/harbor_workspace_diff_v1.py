"""Bounded before/after workspace measurement for the experimental Harbor path.

This module never follows symlinks, never writes into the measured tree, and
skips VCS metadata and dependency/build caches. The caller chooses the state
file path and is expected to keep it in /tmp. Measurement is honest accounting
for disposable task containers; it is NOT a sandbox, a confinement proof, or a
verifier. Limit breaches are reported, never silently absorbed.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import sys

MARKER = "BRAIN_WORKSPACE_DIFF_V1:"
MAX_ENTRIES = 20_000
MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_TOTAL_BYTES = 256 * 1024 * 1024
MAX_STATE_BYTES = 64 * 1024 * 1024
MAX_REPORTED_PATHS = 25
SKIPPED_DIRS = frozenset({
    '.git', '.hg', '.svn', '__pycache__', '.pytest_cache', '.mypy_cache',
    '.ruff_cache', '.tox', '.venv', 'venv', 'node_modules', 'dist', 'build',
    'coverage', 'out', 'target', '.next', '.nuxt', '.cache', '.parcel-cache',
    '.turbo',
})


class WorkspaceDiffError(ValueError):
    pass


def _collect(root: str | Path) -> dict[str, tuple[int, str]]:
    base = Path(root)
    if not base.is_absolute():
        raise WorkspaceDiffError('ABSOLUTE_ROOT_REQUIRED')
    if not base.is_dir():
        raise WorkspaceDiffError('ROOT_UNAVAILABLE')
    found: dict[str, tuple[int, str]] = {}
    entries = total = skipped = 0
    for current, dirs, files in os.walk(base, followlinks=False):
        kept = []
        for name in dirs:
            if name in SKIPPED_DIRS or name.startswith('.'):
                skipped += 1
                continue
            kept.append(name)
        dirs[:] = kept
        rel_dir = Path(current).relative_to(base)
        for name in sorted(files):
            entries += 1
            if entries > MAX_ENTRIES:
                raise WorkspaceDiffError('ENTRY_LIMIT')
            rel = str(rel_dir / name) if str(rel_dir) != '.' else name
            full = Path(current) / name
            try:
                st = os.lstat(full)
            except OSError:
                skipped += 1
                continue
            if not stat.S_ISREG(st.st_mode):
                skipped += 1
                continue
            if st.st_size > MAX_FILE_BYTES:
                skipped += 1
                found[rel] = (-1, 'SKIPPED_TOO_LARGE')
                continue
            if total + st.st_size > MAX_TOTAL_BYTES:
                raise WorkspaceDiffError('BYTE_LIMIT')
            digest = hashlib.sha256()
            try:
                with open(full, 'rb') as handle:
                    while True:
                        chunk = handle.read(65536)
                        if not chunk:
                            break
                        digest.update(chunk)
                        total += len(chunk)
                        if total > MAX_TOTAL_BYTES:
                            raise WorkspaceDiffError('BYTE_LIMIT')
            except OSError:
                skipped += 1
                continue
            found[rel] = (st.st_size, digest.hexdigest())
    found['__meta__'] = (skipped, f'symlinks_or_skipped={skipped};entries={entries};bytes={total}', total)
    return found


def _write_state(state_path: str | Path, payload: dict) -> None:
    raw = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')
    if len(raw) > MAX_STATE_BYTES:
        raise WorkspaceDiffError('STATE_TOO_LARGE')
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW
    fd = os.open(str(state_path), flags, 0o600)
    try:
        os.write(fd, raw)
    finally:
        os.close(fd)


def _read_state(state_path: str | Path) -> dict[str, list]:
    raw = Path(state_path).read_bytes()
    if len(raw) > MAX_STATE_BYTES:
        raise WorkspaceDiffError('STATE_TOO_LARGE')
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise WorkspaceDiffError('STATE_INVALID')
    return data


def snapshot(root: str | Path, state_path: str | Path) -> dict:
    files = _collect(root)
    meta = files.pop('__meta__', (0, '', 0))
    _write_state(state_path, {k: [int(v[0]), v[1]] for k, v in files.items()})
    return {'status': 'SNAPSHOT', 'files': len(files),
            'bytes_hashed': int(meta[2]) if len(meta) > 2 else 0,
            'skipped': int(meta[0]),
            'note': 'bounded snapshot; symlinks and caches skipped; untrusted'}


def diff(root: str | Path, state_path: str | Path) -> dict:
    before = _read_state(state_path)
    before.pop('__meta__', None)
    after = _collect(root)
    meta = after.pop('__meta__', (0, ''))
    added = sorted(k for k in after if k not in before)
    removed = sorted(k for k in before if k not in after)
    changed = sorted(k for k in after if k in before and after[k][1] != before[k][1])
    diff_bytes = int(
        sum(after[k][0] for k in added if after[k][0] >= 0)
        + sum(after[k][0] for k in changed if after[k][0] >= 0)
    )
    return {'status': 'DIFF',
            'added': len(added), 'removed': len(removed), 'changed': len(changed),
            'diff_bytes': diff_bytes,
            'candidate_changed': bool(added or removed or changed),
            'changed_paths': (added + changed)[:MAX_REPORTED_PATHS],
            'removed_paths': removed[:MAX_REPORTED_PATHS],
            'skipped': int(meta[0]) if isinstance(meta, tuple) else 0,
            'note': 'bounded cumulative workspace measurement; untrusted; not verification'}


def main() -> int:
    if len(sys.argv) != 4 or sys.argv[1] not in ('snapshot', 'diff'):
        raise WorkspaceDiffError('USAGE: harbor_workspace_diff_v1.py snapshot|diff ROOT STATE_PATH')
    try:
        report = (snapshot if sys.argv[1] == 'snapshot' else diff)(sys.argv[2], sys.argv[3])
    except (WorkspaceDiffError, OSError, ValueError, json.JSONDecodeError) as exc:
        report = {'status': 'ERROR', 'error': type(exc).__name__ + ':' + str(exc)[:200]}
    print(MARKER + json.dumps(report, sort_keys=True), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

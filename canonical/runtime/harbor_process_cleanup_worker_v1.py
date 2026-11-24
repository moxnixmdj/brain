#!/usr/bin/env python3
"""Best-effort task-container process cleanup for explicit disposable-VM runs.

Snapshots PID/start-time pairs, then sends SIGKILL to newly observed processes
except the cleanup process and its ancestors. A PID may race or escape detection;
baseline processes may fork, and exited workers may have external effects. This
is not proof of quiescence. Never run the cleanup against the host. Only use in a
checked private PID namespace; it intentionally kills processes in that container.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import signal
import sys
import time

MARKER = 'BRAIN_PROCESS_CLEANUP_V1:'
LIMIT = 4096


def _stat(pid: int) -> tuple[int, int] | None:
    try:
        data = (Path('/proc') / str(pid) / 'stat').read_text(encoding='ascii')
        fields = data[data.rfind(')') + 2:].split()
        return int(fields[1]), int(fields[19])  # PPID and starttime
    except (OSError, ValueError, IndexError):
        return None


def snapshot() -> dict[str, int]:
    out = {}
    for entry in os.listdir('/proc'):
        if entry.isdecimal():
            info = _stat(int(entry))
            if info is not None:
                out[entry] = info[1]
    if not out or len(out) > LIMIT:
        raise ValueError('PROCESS_SNAPSHOT_INVALID')
    return out


def _ancestors() -> set[str]:
    result = {'1'}
    pid = os.getpid()
    for _ in range(256):
        if pid <= 0 or str(pid) in result:
            break
        result.add(str(pid))
        info = _stat(pid)
        if info is None:
            break
        pid = info[0]
    return result


def cleanup(baseline: dict[str, int]) -> dict:
    if (not isinstance(baseline, dict) or not baseline or len(baseline) > LIMIT
            or any(not isinstance(k, str) or not k.isdecimal() or type(v) is not int or v < 0
                   for k, v in baseline.items())):
        raise ValueError('BASELINE_INVALID')
    killed: list[int] = []
    for _ in range(4):
        current = snapshot()
        protected = _ancestors()
        candidates = [(int(pid), tick) for pid, tick in current.items()
                      if pid not in protected and baseline.get(pid) != tick]
        if not candidates:
            return {'status': 'NO_NEW_VISIBLE_PROCESSES', 'killed_pids': killed,
                    'quiescence_verified': False}
        for pid, tick in candidates:
            # Re-read immediately before signaling to reduce, but not eliminate,
            # the PID reuse race. Never signal a protected ancestor.
            info = _stat(pid)
            if info is None or info[1] != tick or str(pid) in _ancestors():
                continue
            try:
                os.kill(pid, signal.SIGKILL)
                killed.append(pid)
            except ProcessLookupError:
                pass
            except PermissionError as exc:
                raise ValueError('PROCESS_SIGNAL_DENIED') from exc
        time.sleep(0.05)
    current = snapshot()
    protected = _ancestors()
    if any(pid not in protected and baseline.get(pid) != tick for pid, tick in current.items()):
        raise ValueError('NEW_PROCESSES_REMAIN')
    return {'status': 'NO_NEW_VISIBLE_PROCESSES', 'killed_pids': killed,
            'quiescence_verified': False}


def main() -> int:
    try:
        if len(sys.argv) == 2 and sys.argv[1] == 'snapshot':
            result = {'baseline': snapshot(), 'quiescence_verified': False}
        elif len(sys.argv) == 3 and sys.argv[1] == 'cleanup':
            payload = base64.b64decode(sys.argv[2], validate=True)
            if len(payload) > 100_000:
                raise ValueError('BASELINE_TOO_LARGE')
            result = cleanup(json.loads(payload))
        else:
            raise ValueError('MODE_INVALID')
        print(MARKER + json.dumps(result, sort_keys=True), flush=True)
        return 0
    except (OSError, ValueError, UnicodeError) as exc:
        print('BRAIN_PROCESS_CLEANUP_REFUSED:' + str(exc)[:200], file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
"""Research harness for *one* pinned historical living-agent canary.

Linux user/mount/network/PID namespaces and a chroot hide the caller's root and
make host /usr read-only. The canary uses a disposable /work, never caller data.
This is not a hardened sandbox for hostile code: host /usr remains readable,
there is no seccomp policy or cgroup resource accounting, and kernel attacks
are outside its boundary. Never use this harness to execute untrusted Python.
It intentionally is not wired into the live front door or the agent's actions.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import tempfile
from typing import Any, Mapping

# The four modules extracted from commit 207a2b2d7d20fe31c79a2921e7c3dd19a9158001.
PINNED = {
    'living_agent_v1': '212e349c5c5b4ef5e34c657855ef3fb8c00fc1f862edadf7f059a6d2be6a4710',
    'living_core_v1': 'f1fa8262d653b5ca809125b3e787bcb30c316acc4b8fd598fce53ac942c5897a',
    'living_discovery_v1': 'e64a4a324a30fc0ac295ce81dcebf5f36a7ce6d205917b0df21d6f6f37b3738b',
    'shell_synthesis_v1': 'c9e0ab8a7dbdaa3e072daef43dbc4a9b68451bc12a461391e7e951eb09ce49a3',
}
MAX_REQUEST_BYTES = 100_000

_WORKER = r'''import json, os, resource, sys
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
resource.setrlimit(resource.RLIMIT_FSIZE, (4_000_000, 4_000_000))
resource.setrlimit(resource.RLIMIT_CPU, (8, 8))
resource.setrlimit(resource.RLIMIT_AS, (512_000_000, 512_000_000))
os.chdir('/work')
from canonical.runtime.living_agent_v1 import LivingAgent, ShellSkill
try:
    skill = ShellSkill.from_dict(json.load(sys.stdin))
    ok = LivingAgent('/work')._canary_ok(skill)
    print(json.dumps({'status': 'CANARY_PASS' if ok else 'CANARY_FAILED', 'pass': ok}))
except Exception as exc:
    print(json.dumps({'status': 'CANARY_ERROR', 'pass': False, 'error_type': type(exc).__name__}))
'''

# This shell runs as namespace root only to establish mounts and chroot. The
# candidate runs after all capabilities are removed and no_new_privs is set.
_SETUP = r'''set -eu
root="$1"
mount --make-rprivate /
mount --bind /usr "$root/usr"
mount -o remount,bind,ro,nosuid,nodev "$root/usr"
mount --bind /dev/null "$root/dev/null"
exec /usr/sbin/chroot "$root" /usr/bin/setpriv --bounding-set=-all --inh-caps=-all --ambient-caps=-all --no-new-privs /usr/bin/python3 -I /source/worker.py
'''


def evaluate_canary(source: str | Path, skill: Mapping[str, Any], *, timeout: float = 15.0) -> dict[str, Any]:
    """Run the historical _canary_ok on a copied skill, or fail closed.

    `source` must be the exact trusted four-module historical snapshot. The
    actual task workspace and arbitrary caller files are never mounted. Skills
    are JSON data, but this limited research boundary does not justify accepting
    adversarial skills in a production service.
    """
    if not isinstance(skill, Mapping) or not math.isfinite(timeout) or timeout <= 0 or timeout > 30:
        raise ValueError('INVALID_REQUEST')
    request = json.dumps(dict(skill), ensure_ascii=True, allow_nan=False).encode()
    if len(request) > MAX_REQUEST_BYTES:
        raise ValueError('REQUEST_TOO_LARGE')
    files: dict[str, bytes] = {}
    for name, digest in PINNED.items():
        data = (Path(source) / 'canonical' / 'runtime' / (name + '.py')).read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError('HISTORICAL_SOURCE_HASH_MISMATCH:' + name)
        files[name] = data
    with tempfile.TemporaryDirectory(prefix='living_canary_') as temp:
        root = Path(temp)
        for directory in ('usr', 'work', 'tmp', 'dev', 'source/canonical/runtime'):
            (root / directory).mkdir(parents=True, exist_ok=True)
        (root / 'dev/null').touch()
        # Debian-style merged /usr, required by the pinned shell and interpreter.
        for name in ('bin', 'sbin', 'lib', 'lib64'):
            (root / name).symlink_to('usr/' + name)
        (root / 'source' / 'worker.py').write_text(
            "import sys\nsys.path.insert(0, '/source')\n" + _WORKER, encoding='utf-8')
        for name, data in files.items():
            (root / 'source/canonical/runtime' / (name + '.py')).write_bytes(data)
        argv = ['/usr/bin/unshare', '--user', '--map-root-user', '--mount', '--net',
                '--pid', '--fork', '--kill-child', '/bin/sh', '-c', _SETUP, 'setup', str(root)]
        env = {'PATH': '/usr/bin:/bin', 'HOME': '/work', 'TMPDIR': '/tmp',
               'LC_ALL': 'C', 'PYTHONDONTWRITEBYTECODE': '1'}
        try:
            process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, env=env, start_new_session=True)
            try:
                stdout, stderr = process.communicate(request, timeout=timeout)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.communicate()
                return {'status': 'ISOLATION_TIMEOUT', 'pass': False}
        except OSError as exc:
            return {'status': 'ISOLATION_UNAVAILABLE', 'pass': False,
                    'error_type': type(exc).__name__}
        if process.returncode != 0:
            return {'status': 'ISOLATION_FAILED', 'pass': False,
                    'exit_code': process.returncode,
                    'error': stderr.decode('utf-8', errors='replace')[:1000]}
        try:
            result = json.loads(stdout)
        except (ValueError, UnicodeDecodeError):
            return {'status': 'ISOLATION_INVALID_RESULT', 'pass': False}
        if not isinstance(result, dict) or result.get('status') not in {
                'CANARY_PASS', 'CANARY_FAILED', 'CANARY_ERROR'}:
            return {'status': 'ISOLATION_INVALID_RESULT', 'pass': False}
        return result

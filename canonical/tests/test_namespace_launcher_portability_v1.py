"""Actual syscall-root, explicit device policy, and descendant cleanup."""
import json
from pathlib import Path
import uuid

import pytest

from canonical.runtime import zero_ambient_namespace_launcher_v1 as launcher
from canonical.tests.test_zero_ambient_namespace_launcher_v1 import write_input, policy


def test_syscall_root_resets_cwd_and_only_opted_in_device_is_visible():
    td, root = write_input({'c.py': '''\
        import json, os, pathlib, stat
        with open('/dev/null', 'wb') as f: f.write(b'discarded')
        with open('/dev/null', 'rb') as f: empty = f.read() == b''
        payload = {'cwd': os.getcwd(), 'empty': empty,
                   'char': stat.S_ISCHR(os.stat('/dev/null').st_mode),
                   'devices': sorted(p.name for p in pathlib.Path('/dev').iterdir()),
                   'hidden': all(not pathlib.Path(p).exists() for p in ['/proc', '/sys', '/home', '/etc'])}
        os.write(int(os.environ['PROJECT_BRAIN_BROKER_FD']), json.dumps(payload).encode())
    '''})
    try:
        p = {**policy(root, 'c.py'), 'expose_null_device': True}
        r = launcher.run_confined(p)
        assert r['returncode'] == 0
        assert json.loads(r['broker_payload']) == {
            'cwd': '/', 'empty': True, 'char': True, 'devices': ['null'], 'hidden': True}
        assert launcher.policy_sha256(p) != launcher.policy_sha256({**p, 'expose_null_device': False})
    finally:
        td.cleanup()


@pytest.mark.parametrize('value', ['true', 1, None, []])
def test_device_authority_is_not_truthiness(value):
    td, root = write_input({'c.py': 'pass\n'})
    try:
        with pytest.raises(launcher.NamespaceConfinementError, match='NULL_DEVICE_POLICY_MUST_BE_BOOLEAN'):
            launcher.canonical_policy({**policy(root, 'c.py'), 'expose_null_device': value})
    finally:
        td.cleanup()


def test_wallclock_kills_even_a_new_session_descendant():
    marker = 'ns-descendant-' + uuid.uuid4().hex
    td, root = write_input({'c.py': '''\
        import os, time
        if os.fork() == 0:
            os.setsid()
            os.write(int(os.environ['PROJECT_BRAIN_BROKER_FD']), b'descendant-started')
            time.sleep(60)
        else:
            time.sleep(60)
    '''})
    try:
        r = launcher.run_confined(policy(root, 'c.py', marker, wallclock_s=1))
        assert r['status'] == 'WALLCLOCK_LIMIT_EXCEEDED'
        assert r['broker_payload'] == b'descendant-started'
        remaining = []
        for proc in Path('/proc').glob('[0-9]*/cmdline'):
            try:
                cmdline = proc.read_bytes().split(b'\0')
            except OSError:
                continue
            if marker.encode() in cmdline:
                remaining.append(str(proc))
        assert remaining == []
    finally:
        td.cleanup()

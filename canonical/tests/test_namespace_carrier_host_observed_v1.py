"""Controlled host-observed candidate checks, NOT independent qualification.

All targets are temporary sentinels owned by this test. No real secret, cloud
service or sensitive file is used. A skip or error means the qualification gate
is incomplete. The namespace worker has no repair/front-door authority here.
"""
from __future__ import annotations

import base64
import copy
import ctypes
import json
import os
from pathlib import Path
import select
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

from canonical.runtime import brokered_workspace_execution_v1 as broker
from canonical.runtime import zero_ambient_namespace_launcher_v1 as launcher


LIMITS = {'pids': 16, 'memory_mb': 128, 'cpu_seconds': 10, 'wallclock_s': 5,
          'scratch_mb': 16, 'max_file_mb': 2, 'nofile': 32, 'broker_max_bytes': 65536}
HELPER = '''import json,sys
from canonical.runtime import zero_ambient_namespace_launcher_v1 as ns
policy=json.loads(sys.argv[1])
r=ns.run_confined(policy)
r['broker_payload']=r['broker_payload'].decode('utf-8','replace')
print(json.dumps(r),flush=True)
'''


def children(pid):
    found = set()
    try:
        pending = [pid]
        while pending:
            p = pending.pop()
            try:
                raw = Path(f'/proc/{p}/task/{p}/children').read_text().split()
            except (FileNotFoundError, ProcessLookupError):
                continue
            for value in raw:
                child = int(value)
                if child not in found:
                    found.add(child); pending.append(child)
    except PermissionError:
        raise AssertionError('host cannot observe process descendants')
    return found


def proc_identity(pid):
    try:
        # starttime guards against confusing PID reuse for a surviving child.
        data = Path(f'/proc/{pid}/stat').read_text()
        tail = data[data.rfind(')') + 2:].split()
        return pid, tail[19]
    except (FileNotFoundError, ProcessLookupError):
        return None


def still_alive(identity):
    return proc_identity(identity[0]) == identity


def process_state(identity):
    if not still_alive(identity):
        return 'gone'
    try:
        data = Path(f'/proc/{identity[0]}/stat').read_text()
        return data[data.rfind(')') + 2:].split()[0]
    except (FileNotFoundError, ProcessLookupError):
        return 'gone'


@unittest.skipUnless(sys.platform.startswith('linux'), 'requires Linux host /proc and namespaces')
class HostObservedNamespaceTests(unittest.TestCase):
    def setUp(self):
        if not broker.namespace_broker_available():
            self.skipTest('candidate namespace launcher unavailable; NOT QUALIFIED')
        self.temp = tempfile.TemporaryDirectory(prefix='namespace_host_probe_')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inp = self.root / 'input'; self.inp.mkdir()

    def policy(self, *args, wallclock=5):
        return {'argv': ['/usr/bin/python3', '-I', '/input/qualification_worker.py', *map(str, args)],
                'input_dir': str(self.inp), 'limits': {**LIMITS, 'wallclock_s': wallclock}}

    def worker(self, text):
        (self.inp / 'qualification_worker.py').write_text(text, encoding='utf-8')

    def launch(self, policy, *, env=None, pass_fds=()):
        child_env = dict(os.environ if env is None else env)
        child_env['TMPDIR'] = str(self.root)
        return subprocess.Popen([sys.executable, '-c', HELPER, json.dumps(policy)],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                env=child_env, pass_fds=pass_fds, start_new_session=True)

    def await_workers(self, proc, count=1):
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline:
            result = []
            for pid in children(proc.pid):
                try:
                    command = Path(f'/proc/{pid}/cmdline').read_bytes()
                except (FileNotFoundError, ProcessLookupError):
                    continue
                parts = command.split(b'\0')
                if (len(parts) > 2 and parts[0].rsplit(b'/', 1)[-1].startswith(b'python')
                        and parts[1:3] == [b'-I', b'/input/qualification_worker.py']):
                    ident = proc_identity(pid)
                    if ident: result.append(ident)
            if len(result) >= count:
                return result
            if proc.poll() is not None:
                break
            time.sleep(.025)
        raise AssertionError('host did not observe required running worker processes')

    def cleanup_processes(self, proc, identities):
        # Cleanup of this test's own controlled descendants even if a check fails.
        for pid, start in identities:
            if still_alive((pid, start)):
                try: os.kill(pid, signal.SIGKILL)
                except ProcessLookupError: pass
        if proc.poll() is None:
            proc.kill()
        try: proc.communicate(timeout=5)
        except subprocess.TimeoutExpired: pass

    def test_host_sentinels_and_local_listeners_observe_no_escape(self):
        sentinel = self.root / 'sentinel'; sentinel.write_bytes(b'HOST_SENTINEL')
        (self.inp / 'outside-link').symlink_to(sentinel)
        # Monitor real access/modification events on the host, before worker runs.
        libc = ctypes.CDLL(None, use_errno=True)
        inotify = libc.inotify_init1(os.O_NONBLOCK | os.O_CLOEXEC)
        self.assertGreaterEqual(inotify, 0, 'inotify unavailable: cannot observe host reads')
        self.addCleanup(os.close, inotify)
        watch = libc.inotify_add_watch(inotify, os.fsencode(sentinel), 0x1 | 0x2 | 0x4 | 0x8)
        self.assertGreaterEqual(watch, 0, 'inotify watch failed')
        fd = os.open(sentinel, os.O_WRONLY | os.O_APPEND)
        self.addCleanup(os.close, fd)
        os.set_inheritable(fd, True)
        tcp = socket.socket(); tcp.bind(('0.0.0.0', 0)); tcp.listen(4); tcp.setblocking(False)
        # Route lookup via UDP connect does not send traffic. A non-loopback
        # address makes a second host-observed listener target available.
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as route:
            route.connect(('192.0.2.1', 9))
            host_address = route.getsockname()[0]
        self.assertFalse(host_address.startswith('127.'), 'no host non-loopback target')
        unix = socket.socket(socket.AF_UNIX); sockname = '\0hostprobe_' + str(os.getpid()) + '_' + str(time.time_ns())
        unix.bind(sockname); unix.listen(4); unix.setblocking(False)
        self.addCleanup(tcp.close); self.addCleanup(unix.close)
        self.worker('''import os,socket,subprocess,sys
sentinel,fd,port,name,hostip=sys.argv[1],int(sys.argv[2]),int(sys.argv[3]),sys.argv[4],sys.argv[5]
def attempt(f):
    try: f()
    except (OSError,ValueError): pass
for p in (sentinel, '/input/outside-link', '/input/../'+sentinel.lstrip('/')):
    attempt(lambda p=p: open(p,'rb').read())
    attempt(lambda p=p: open(p,'ab').write(b'ESCAPE'))
attempt(lambda: os.write(fd,b'FD_ESCAPE'))
attempt(lambda: os.link('/input/outside-link','/work/hardlink',follow_symlinks=True))
attempt(lambda: os.symlink(sentinel,'/work/swap'))
attempt(lambda: open('/work/swap','ab').write(b'SWAP'))
for i in range(30):
    def swap(i=i):
        replacement='/work/swap_next'
        if os.path.lexists(replacement): os.unlink(replacement)
        os.symlink(sentinel if i%2 else '/input/outside-link', replacement)
        os.replace(replacement,'/work/swap')
        open('/work/swap','ab').write(b'SWAP')
    attempt(swap)
attempt(lambda: subprocess.run(['/usr/bin/mount','--bind','/input','/work'],timeout=2))
for family,address in ((socket.AF_INET,('127.0.0.1',port)),(socket.AF_INET,(hostip,port)),(socket.AF_INET,('192.0.2.1',9)),(socket.AF_UNIX,'\\0'+name)):
    def connect(family=family,address=address):
        s=socket.socket(family); s.settimeout(.2); s.connect(address); s.sendall(b'CONNECTION'); s.close()
    attempt(connect)
os.write(int(os.environ['PROJECT_BRAIN_BROKER_FD']),b'probe completed')
''')
        proc = self.launch(self.policy(sentinel, fd, tcp.getsockname()[1], sockname[1:], host_address), pass_fds=(fd,))
        out, err = proc.communicate(timeout=15)
        self.assertEqual(proc.returncode, 0, err.decode(errors='replace'))
        result = json.loads(out)
        self.assertEqual(result['returncode'], 0, result)
        self.assertEqual(result['broker_payload'], 'probe completed')  # liveness only
        ready, _, _ = select.select([inotify, tcp, unix], [], [], .2)
        events = os.read(inotify, 65536) if inotify in ready else b''
        self.assertEqual(events, b'', 'host observed an access or mutation of sentinel')
        self.assertNotIn(tcp, ready, 'host TCP listener received connection')
        self.assertNotIn(unix, ready, 'host Unix listener received connection')
        self.assertEqual(sentinel.read_bytes(), b'HOST_SENTINEL')

    def test_host_observes_timeout_kills_all_observed_workers(self):
        self.worker('''import os,time
if os.fork()==0:
    while True: time.sleep(.2)
while True: time.sleep(.2)
''')
        proc = self.launch(self.policy(wallclock=4)); seen = []
        try:
            seen = self.await_workers(proc, count=2)
            out, err = proc.communicate(timeout=15)
            self.assertEqual(proc.returncode, 0, err.decode(errors='replace'))
            self.assertEqual(json.loads(out)['status'], 'WALLCLOCK_LIMIT_EXCEEDED')
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline and any(still_alive(x) for x in seen):
                time.sleep(.05)
            self.assertFalse([x for x in seen if still_alive(x)], 'worker descendants survived timeout')
        finally:
            self.cleanup_processes(proc, seen)

    def test_host_inspects_worker_environment(self):
        self.worker('import time\nwhile True: time.sleep(.2)\n')
        env = dict(os.environ, AWS_SECRET_ACCESS_KEY='fake_aws_do_not_use_8142', GITHUB_TOKEN='fake_github_do_not_use_7628')
        proc = self.launch(self.policy(wallclock=4), env=env); seen = []
        try:
            seen = self.await_workers(proc)
            try:
                parent_environ = Path(f'/proc/{proc.pid}/environ').read_bytes()
                environ = Path(f'/proc/{seen[0][0]}/environ').read_bytes()
            except PermissionError as exc:
                self.fail('host cannot inspect process /proc environment; qualification unverified: ' + str(exc))
            for value in (b'AWS_SECRET_ACCESS_KEY', b'GITHUB_TOKEN', b'fake_aws_do_not_use_8142', b'fake_github_do_not_use_7628'):
                self.assertIn(value, parent_environ, 'fake credential was not seeded in the parent')
                self.assertNotIn(value, environ)
            out, err = proc.communicate(timeout=15)
            self.assertEqual(proc.returncode, 0, err.decode(errors='replace'))
            self.assertEqual(json.loads(out)['status'], 'WALLCLOCK_LIMIT_EXCEEDED')
        finally:
            self.cleanup_processes(proc, seen)

    def test_external_ip_egress_observed_by_host(self):
        try:
            monitor = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(3))
        except PermissionError:
            self.skipTest('host denied packet capture (CAP_NET_RAW); external egress NOT QUALIFIED')
        else:
            monitor.close()
            self.fail('host packet capture is available but an external egress observer is not implemented')

    def test_host_observes_runtime_python_environ(self):
        # Trusted probe materializes a uniquely framed copy of its live mapping;
        # the host reads process memory directly, not a worker pass/fail claim.
        # This checks this fixture, not arbitrary hostile interpreter memory.
        token = str(os.getpid()) + '_' + str(time.time_ns())
        self.worker('''import json,os,sys,time
key=sys.argv[1]
os.environ['INTERNAL_ENV_PROBE']=key
start=('ENVBEGIN_'+key+'_').encode()
end=('_ENVEND_'+key).encode()
hold=start+json.dumps(dict(os.environ),sort_keys=True).encode()+end
while True: time.sleep(.2)
''')
        env = dict(os.environ, AWS_SECRET_ACCESS_KEY='fake_aws_dynamic_8142', GITHUB_TOKEN='fake_github_dynamic_7628')
        proc = self.launch(self.policy(token, wallclock=8), env=env); seen = []
        try:
            seen = self.await_workers(proc)
            pid = seen[0][0]
            start = ('ENVBEGIN_' + token + '_').encode()
            end = ('_ENVEND_' + token).encode()
            found = None
            deadline = time.monotonic() + 4
            while found is None and time.monotonic() < deadline:
                maps = Path(f'/proc/{pid}/maps').read_text().splitlines()
                try:
                    memfd = os.open(f'/proc/{pid}/mem', os.O_RDONLY)
                except OSError as exc:
                    self.fail('host cannot inspect live process memory: ' + str(exc))
                try:
                    for line in maps:
                        fields = line.split(maxsplit=5)
                        if len(fields) < 2 or not fields[1].startswith('rw'):
                            continue
                        bounds = fields[0].split('-')
                        lo, hi = int(bounds[0], 16), int(bounds[1], 16)
                        if hi - lo > 64 * 1024 * 1024:
                            continue
                        try: data = os.pread(memfd, hi - lo, lo)
                        except OSError: continue
                        pos = data.find(start)
                        while pos >= 0:
                            finish = data.find(end, pos + len(start), pos + len(start) + 16384)
                            if finish >= 0:
                                try: candidate = json.loads(data[pos+len(start):finish])
                                except (ValueError, UnicodeError): candidate = None
                                if isinstance(candidate, dict) and candidate.get('INTERNAL_ENV_PROBE') == token:
                                    found = candidate
                                    break
                            pos = data.find(start, pos + 1)
                        if found is not None: break
                finally:
                    os.close(memfd)
                if found is None: time.sleep(.03)
            self.assertIsNotNone(found, 'host could not observe the live environment fixture')
            self.assertEqual(found['INTERNAL_ENV_PROBE'], token)
            for name, value in (('AWS_SECRET_ACCESS_KEY', 'fake_aws_dynamic_8142'),
                                ('GITHUB_TOKEN', 'fake_github_dynamic_7628')):
                self.assertNotIn(name, found)
                self.assertNotIn(value, found.values())
        finally:
            self.cleanup_processes(proc, seen)

    def test_host_observes_nested_input_mount_refusal(self):
        nested = self.inp / 'nested'; nested.mkdir()
        source = self.root / 'mount_source'; source.mkdir()
        marker = self.root / 'worker_must_not_run'
        # The nested mount exists only in this disposable mount namespace.
        # No carrier workload is started; policy must refuse before launch.
        script = '''import pathlib,subprocess,sys
from canonical.runtime import zero_ambient_namespace_launcher_v1 as n
source, nested, inp, marker = sys.argv[1:]
subprocess.run(['/usr/bin/mount','--bind',source,nested],check=True)
try:
    n.canonical_policy({'argv':['/usr/bin/true'], 'input_dir':inp})
except n.NamespaceConfinementError as exc:
    if not str(exc).startswith('INPUT_DIR_HAS_NESTED_MOUNTS:'): raise
else:
    pathlib.Path(marker).write_text('incorrectly accepted')
    raise SystemExit(1)
'''
        proc = subprocess.run(['unshare','--user','--map-root-user','--mount','--fork',
                               sys.executable,'-c',script,str(source),str(nested),str(self.inp),str(marker)],
                              capture_output=True, text=True, timeout=20)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse(marker.exists(), 'nested-mount input was accepted')
        self.assertNotIn(str(nested), Path('/proc/self/mountinfo').read_text(),
                         'nested test mount leaked into host mount namespace')

    def check_supervisor_termination(self, sig):
        self.worker('''import os,time
if os.fork()==0:
    os.setsid()  # escaping the launcher's process group must not evade PID-1 cleanup
    while True: time.sleep(.2)
while True: time.sleep(.2)
''')
        proc = self.launch(self.policy(wallclock=15)); seen = []
        try:
            workers = self.await_workers(proc, count=2)
            seen = [ident for pid in children(proc.pid) if (ident := proc_identity(pid))]
            self.assertTrue(all(worker in seen for worker in workers))
            deadline = time.monotonic() + 1
            while time.monotonic() < deadline and len({os.getpgid(x[0]) for x in workers}) < 2:
                time.sleep(.01)
            self.assertEqual(len({os.getpgid(x[0]) for x in workers}), 2,
                             'host did not observe a child in a separate session')
            proc.send_signal(sig)
            proc.wait(timeout=5)
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline and any(still_alive(x) for x in workers):
                time.sleep(.05)
            survivors = [(x, process_state(x)) for x in workers if still_alive(x)]
            self.assertFalse(survivors, 'host observed workers survive supervisor cancellation')
        finally:
            self.cleanup_processes(proc, seen)

    def test_missing_pidfd_refuses_before_workload(self):
        self.worker('raise RuntimeError("must not execute")\n')
        with mock.patch.object(launcher.os, 'pidfd_open', side_effect=OSError('not supported')):
            with self.assertRaisesRegex(launcher.NamespaceConfinementError, 'LIVENESS_PIDFD_UNAVAILABLE'):
                launcher.run_confined(self.policy())

    def test_pid1_guard_with_dead_launcher_never_starts_workload(self):
        marker = self.root / 'should_not_start'
        dead = subprocess.Popen(['/usr/bin/true'])
        pidfd = os.pidfd_open(dead.pid, 0)
        dead.wait(timeout=5)
        try:
            cmd = ['unshare','--user','--map-root-user','--pid','--fork',sys.executable,
                   '-I','-c',launcher._PID1_GUARD,str(pidfd),'-1',sys.executable,
                   '-c',f'from pathlib import Path; Path({str(marker)!r}).write_text("bad")']
            result = subprocess.run(cmd, pass_fds=(pidfd,), capture_output=True, timeout=15)
            self.assertEqual(result.returncode, 126, result.stderr.decode(errors='replace'))
            self.assertFalse(marker.exists())
        finally:
            os.close(pidfd)

    def test_host_observes_sigterm_kills_descendants(self):
        self.check_supervisor_termination(signal.SIGTERM)

    def test_host_observes_sigkill_kills_descendants(self):
        self.check_supervisor_termination(signal.SIGKILL)

    def test_host_observes_persistent_worker_after_supervisor_sigkill(self):
        script = '''import time
from canonical.runtime.brokered_workspace_execution_v1 import PersistentConfinedZygote
z=PersistentConfinedZygote(); z._ensure_started(); print('ready',flush=True)
while True: time.sleep(.2)
'''
        env = dict(os.environ, TMPDIR=str(self.root))
        proc = subprocess.Popen([sys.executable, '-c', script], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, env=env, start_new_session=True)
        seen = []
        try:
            ready, _, _ = select.select([proc.stdout], [], [], 8)
            self.assertTrue(ready, 'persistent supervisor did not signal ready')
            self.assertEqual(proc.stdout.readline(), b'ready\n')
            seen = [ident for pid in children(proc.pid) if (ident := proc_identity(pid))]
            daemons = []
            for ident in seen:
                try: parts = Path(f'/proc/{ident[0]}/cmdline').read_bytes().split(b'\0')
                except (FileNotFoundError, ProcessLookupError): continue
                if len(parts) > 3 and parts[1:3] == [b'-I', b'-c'] and parts[3].startswith(b'\nimport ast, contextlib'):
                    daemons.append(ident)
            self.assertEqual(len(daemons), 1, 'host did not observe the persistent daemon')
            proc.kill(); proc.wait(timeout=5)
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline and any(still_alive(x) for x in daemons):
                time.sleep(.05)
            survivors = [(x, process_state(x)) for x in daemons if still_alive(x)]
            self.assertFalse(survivors, 'persistent daemon survived supervisor SIGKILL')
        finally:
            self.cleanup_processes(proc, seen)

    def test_host_collector_refuses_duplicate_keys_and_worker_failure(self):
        from canonical.tools import isolated_effect_collector_v1 as collector
        duplicate = b'{"schema":"a","schema":"b","effects":{}}'
        fixtures = [
            ('import os\nos.write(int(os.environ["PROJECT_BRAIN_BROKER_FD"]), ' + repr(duplicate) + ')\n',
             'BROKER_DUPLICATE_KEY'),
            ('import sys\nsys.exit(7)\n', 'CARRIER_DID_NOT_COMPLETE'),
        ]
        for script, reason in fixtures:
            with self.subTest(reason=reason):
                self.worker(script)
                policy = self.policy()
                with self.assertRaisesRegex(collector.CollectionRefused, reason):
                    collector.collect_fixture_effects(
                        policy, base_commit='a'*40, expected_policy_sha256=launcher.policy_sha256(policy),
                        expected_effect_paths=('repair.patch',), expected_patch_path='repair.patch')

    def test_host_collects_and_rechecks_real_carrier_broker_bytes(self):
        from canonical.tools import isolated_effect_collector_v1 as collector
        from canonical.tools import isolated_effect_receipt_verifier_v1 as verifier
        patch = b'diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n-a\n+b\n'
        report = b'{"message":"fixture"}'
        payload = json.dumps({'schema': collector.PAYLOAD_SCHEMA,
                              'effects': {'repair.patch': base64.b64encode(patch).decode(),
                                          'report.json': base64.b64encode(report).decode()}}).encode()
        self.worker('import os\nos.write(int(os.environ["PROJECT_BRAIN_BROKER_FD"]), ' + repr(payload) + ')\n')
        policy = self.policy()
        policy_sha = launcher.policy_sha256(policy)
        result = collector.collect_fixture_effects(
            policy, base_commit='a'*40, expected_policy_sha256=policy_sha,
            expected_effect_paths=('repair.patch', 'report.json'), expected_patch_path='repair.patch')
        self.assertFalse(result['carrier_qualified'])
        self.assertFalse(result['independent_verification'])
        self.assertFalse(result['publication_authority'])
        self.assertEqual(result['patch_bytes'], patch)
        self.assertEqual(result['effect_bytes']['report.json'], report)
        self.assertEqual(result['receipt']['effects']['repair.patch']['sha256'], verifier.digest_bytes(patch))
        params = {'expected_receipt_sha256': result['receipt_sha256'], 'expected_base_commit': 'a'*40,
                  'expected_policy_sha256': policy_sha, 'expected_effect_paths': ('repair.patch', 'report.json'),
                  'expected_patch_path': 'repair.patch'}
        self.assertEqual(verifier.verify_patch(result['receipt'], result['effect_bytes'], **params), patch)
        # Tamper each independently on the actual collected carrier payload.
        for name in ('repair.patch', 'report.json'):
            altered = dict(result['effect_bytes'])
            altered[name] = altered[name][:-1] + bytes([altered[name][-1] ^ 1])
            with self.subTest(tamper=name), self.assertRaises(verifier.ReceiptRefused):
                verifier.verify_patch(result['receipt'], altered, **params)
        for field in ('path', 'base_commit', 'policy_sha256'):
            altered = copy.deepcopy(result['receipt'])
            if field == 'path':
                altered['effects']['other.patch'] = altered['effects'].pop('repair.patch')
            elif field == 'base_commit':
                altered[field] = 'b' * 40
            else:
                altered[field] = 'c' * 64
            # Even if the tampered receipt is rehashed, independent expectations
            # still reject a changed path, base or policy.
            changed_params = {**params, 'expected_receipt_sha256': verifier.receipt_digest(altered)}
            with self.subTest(tamper=field), self.assertRaises(verifier.ReceiptRefused):
                verifier.verify_patch(altered, result['effect_bytes'], **changed_params)


if __name__ == '__main__':
    unittest.main()

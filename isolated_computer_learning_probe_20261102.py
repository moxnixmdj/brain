#!/usr/bin/env python3
"""Research probe: run the existing learner in Brain's namespace launcher.

Runs a current-worktree code snapshot, with only gzip on PATH, synthetic inputs,
read-only /input and explicit memory transfer through the bounded broker. The
launcher mounts host /usr read-only. This is not an independently verified or
production hostile-code sandbox, nor does it connect the learner to the fabric.
Memory imported by this script is from its own trusted prior worker, not arbitrary
untrusted output. The cold arm has empty initial memory, not learning disabled.

Run only on a trusted Linux host with user namespaces, mount and ip support:
    python3 isolated_computer_learning_probe_20261102.py
"""
from __future__ import annotations

import base64
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import tempfile
import time

from canonical.runtime.zero_ambient_namespace_launcher_v1 import run_confined

ROOT = Path(__file__).resolve().parent
STATE_NAMES = ('episodes.json', 'episodes.json.fingerprints.json', 'brain_help_text_v1.json')
MAX_STATE_BYTES = 500_000
WORKER = r'''
import base64, json, os, pathlib, shutil, socket, sys, time
sys.path.insert(0, '/input')
req = json.loads(pathlib.Path('/input/request.json').read_text())
work = pathlib.Path('/work/task'); work.mkdir()
state = pathlib.Path('/work/state'); state.mkdir()
for name in ('episodes.json', 'episodes.json.fingerprints.json', 'brain_help_text_v1.json'):
    previous = pathlib.Path('/input/previous') / name
    if previous.is_file(): shutil.copyfile(previous, state / name)
bin_dir = pathlib.Path('/work/bin'); bin_dir.mkdir()
(bin_dir / 'gzip').symlink_to('/usr/bin/gzip')
os.environ.update(PATH=str(bin_dir), BRAIN_STATE_DIR=str(state),
                  BRAIN_TRANSFER_LEARNING_STATE=str(state / 'episodes.json'),
                  BRAIN_PROGRAM_SYNTHESIS_STATE=str(state / 'synthesis.json'),
                  TMPDIR='/work')
source = work / req['name']
source.write_bytes(base64.b64decode(req['data']))
from canonical.runtime.computer_env_v1 import perform, apply
start = time.monotonic()
result = perform('compress ' + source.name + ' into ' + source.name + '.gz', cwd=work)
out = work / (source.name + '.gz')
wrong = apply({'argv': ['/usr/bin/python3', '-c',
                        'import gzip,sys; sys.stdout.buffer.write(gzip.compress(b"incorrect"))',
                        '{input}'], 'target': 'wrong.gz', 'stdout_to': 'wrong.gz'},
              source, output_name='wrong.gz')
missing = perform('compress absent.txt into absent.txt.gz', cwd=work)
existing_path = work / 'existing.gz'; existing_path.write_bytes(b'protected destination')
existing = apply({'argv': ['/usr/bin/python3', '-c', 'raise SystemExit(99)', '{input}'],
                  'target': 'existing.gz', 'stdout_to': 'existing.gz'},
                 source, output_name='existing.gz')
negative = {'wrong_status': wrong.get('status'), 'wrong_published': (work / 'wrong.gz').exists(),
            'missing_status': missing.get('status'), 'missing_published': (work / 'absent.txt.gz').exists(),
            'existing_status': existing.get('status'),
            'existing_unchanged': existing_path.read_bytes() == b'protected destination'}
checks = {}
try:
    pathlib.Path(req['sentinel']).read_bytes(); checks['host_file_read_blocked'] = False
except OSError: checks['host_file_read_blocked'] = True
try:
    pathlib.Path(req['sentinel']).write_bytes(b'overwritten'); checks['host_file_write_blocked'] = False
except OSError: checks['host_file_write_blocked'] = True
try:
    pathlib.Path('/input/request.json').write_bytes(b'changed'); checks['input_read_only'] = False
except OSError: checks['input_read_only'] = True
try:
    pathlib.Path('/usr/brain_probe_do_not_create').write_bytes(b'x'); checks['system_write_blocked'] = False
except OSError: checks['system_write_blocked'] = True
checks['host_env_secret_absent'] = 'BRAIN_PROBE_FAKE_SECRET' not in os.environ
s = socket.socket(); s.settimeout(.2)
try:
    s.connect(('127.0.0.1', req['outer_port'])); checks['host_network_blocked'] = False
except OSError: checks['host_network_blocked'] = True
finally: s.close()
files = {}
for name in ('episodes.json', 'episodes.json.fingerprints.json', 'brain_help_text_v1.json'):
    p = state / name
    if p.is_file() and p.stat().st_size <= 200000:
        files[name] = base64.b64encode(p.read_bytes()).decode('ascii')
result = {k: result.get(k) for k in ('pass', 'status', 'from_memory', 'learned_by',
                                      'source_content_verified', 'plan')}
body = {'result': result, 'checks': checks, 'negative_controls': negative,
        'elapsed_s': round(time.monotonic()-start, 6),
        'output': base64.b64encode(out.read_bytes()).decode('ascii') if out.is_file() else None,
        'source_unchanged': source.read_bytes() == base64.b64decode(req['data']),
        'memory_files': files}
sock = socket.socket(fileno=int(os.environ['PROJECT_BRAIN_BROKER_FD']))
sock.sendall(json.dumps(body, separators=(',', ':')).encode())
'''
TIMEOUT_WORKER = r'''
import os,socket,time
s=socket.socket(fileno=int(os.environ['PROJECT_BRAIN_BROKER_FD']))
pid=os.fork()
if pid == 0:
    os.setsid(); time.sleep(2.5)
    try: s.sendall(b'LATE')
    except OSError: pass
    os._exit(0)
s.sendall(b'READY'); time.sleep(20)
'''


def source_copy(target: Path) -> None:
    # Snapshot only current runtime/swe-kernel Python source: no user state,
    # credentials, Git metadata, test fixtures, or historic code objects.
    for folder in ('canonical/runtime', 'canonical/swe_kernel'):
        for src in (ROOT / folder).rglob('*.py'):
            if '__pycache__' in src.parts:
                continue
            dst = target / src.relative_to(ROOT)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)


def policy(input_dir: Path, script: str = 'worker.py', wallclock: int = 20) -> dict:
    return {'argv': ['/usr/bin/python3', '-I', '/input/' + script],
            'input_dir': str(input_dir), 'expose_null_device': True,
            'limits': {'pids': 32, 'memory_mb': 512, 'cpu_seconds': 15,
                       'wallclock_s': wallclock, 'scratch_mb': 32,
                       'max_file_mb': 8, 'nofile': 64, 'broker_max_bytes': 1_000_000}}


def run() -> dict:
    with tempfile.TemporaryDirectory(prefix='brain_ns_learning_probe_') as temporary:
        root = Path(temporary)
        code = root / 'input'; code.mkdir()
        source_copy(code)
        (code / 'worker.py').write_text(WORKER, encoding='utf-8')
        (code / 'timeout.py').write_text(TIMEOUT_WORKER, encoding='utf-8')
        sentinel = root / 'host-private-sentinel'
        sentinel.write_bytes(b'host fixture must not change\n')
        before = hashlib.sha256(sentinel.read_bytes()).hexdigest()
        listener = socket.socket(); listener.bind(('127.0.0.1', 0)); listener.listen(1)
        port = listener.getsockname()[1]
        # Prove that this listener is reachable from the host before treating a
        # failed worker connection as evidence of namespace separation.
        with socket.create_connection(('127.0.0.1', port), timeout=1):
            baseline, _ = listener.accept()
            baseline.close()
        listener.setblocking(False)
        contents = {'teach': b'teaching data\n' * 7, 'cold': b'new data\nnext line\n' * 9,
                    'warm': b'new data\nnext line\n' * 9}
        rows = []
        teaching_memory = {}
        env_name = 'BRAIN_PROBE_FAKE_SECRET'
        previous_secret = os.environ.get(env_name)
        os.environ[env_name] = 'not-a-real-secret'
        try:
            for role in ('teach', 'cold', 'warm'):
                previous = code / 'previous'
                if previous.exists(): shutil.rmtree(previous)
                previous.mkdir()
                if role == 'warm':
                    for name, raw in teaching_memory.items():
                        (previous / name).write_bytes(raw)
                name = 'lesson.txt' if role == 'teach' else 'target.txt'
                request = {'name': name, 'data': base64.b64encode(contents[role]).decode(),
                           'sentinel': str(sentinel), 'outer_port': port}
                request_path = code / 'request.json'
                request_path.write_text(json.dumps(request), encoding='utf-8')
                before_request = request_path.read_bytes()
                result = run_confined(policy(code))
                if result['status'] != 'CHILD_EXITED' or result['returncode'] != 0:
                    raise RuntimeError('CONFINED_LEARNER_FAILED:' + result['status'] + ':' + str(result['returncode']))
                data = json.loads(result['broker_payload'])
                restored = {}
                for key, value in data.pop('memory_files').items():
                    if key not in STATE_NAMES:
                        raise ValueError('UNEXPECTED_MEMORY_FILE')
                    restored[key] = base64.b64decode(value, validate=True)
                if sum(map(len, restored.values())) > MAX_STATE_BYTES:
                    raise ValueError('MEMORY_BUNDLE_TOO_LARGE')
                if role == 'teach': teaching_memory = restored
                encoded_output = data.pop('output')
                try:
                    correct = encoded_output is not None and gzip.decompress(
                        base64.b64decode(encoded_output, validate=True)) == contents[role]
                except (OSError, EOFError, ValueError): correct = False
                try:
                    unexpected, _ = listener.accept()
                    unexpected.close()
                    outer_connection_observed = True
                except BlockingIOError:
                    outer_connection_observed = False
                rows.append({'role': role, 'launcher_status': result['status'],
                             'returncode': result['returncode'], 'broker_bytes': result['broker_bytes'],
                             'result': data['result'], 'worker_reported_checks': data['checks'],
                             'worker_reported_negative_controls': data['negative_controls'],
                             'host_listener_connection_observed': outer_connection_observed,
                             'worker_elapsed_s': data['elapsed_s'],
                             'full_external_decompression_matches': correct,
                             'worker_reported_source_unchanged': data['source_unchanged'],
                             'input_file_unchanged': request_path.read_bytes() == before_request,
                             'sentinel_unchanged': hashlib.sha256(sentinel.read_bytes()).hexdigest() == before})
            timeout = run_confined(policy(code, 'timeout.py', wallclock=1))
        finally:
            listener.close()
            if previous_secret is None: os.environ.pop(env_name, None)
            else: os.environ[env_name] = previous_secret
        return {'scope': 'gzip only; current source snapshot; restricted PATH; synthetic files',
                'network': 'private namespace; localhost of outer host tested unreachable',
                'cold_control': 'empty initial transfer store; learning is not disabled',
                'transfer': 'trusted teaching worker memory explicitly copied through bounded broker',
                'authority': 'none; sandbox measurement by producer, not independent verification',
                'limitations': 'host /usr readable; no seccomp or cgroup limits; rlimits per process; '
                               'not a production hostile-code security certification',
                'rows': rows,
                'timeout_control': {'status': timeout['status'], 'returncode': timeout['returncode'],
                                    'broker_payload': timeout['broker_payload'].decode('ascii', 'replace'),
                                    'late_descendant_message_seen': b'LATE' in timeout['broker_payload']}}


def main() -> None:
    print(json.dumps(run(), indent=2))


if __name__ == '__main__':
    main()

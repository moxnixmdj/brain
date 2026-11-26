"""Compare selective vs broad native-test acquisition, without any benchmark grader.

The only selector inputs are base test paths/text and the public goal. Selective
reads six bodies (the discovery output budget); broad reads every eligible body.
Identical final scorer and four-file execution budgets. A pytest observer counts
which test calls actually traverse project functions named in the public text.
Reaching a name, even on a failure, does not establish causality or solve a task.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time


if __name__ == '__main__' and sys.argv[1:2] in (['--observe'], ['--inside']):
    sys.path.insert(0, '/input')
    from goal_native_probe_v1 import named_symbols, observe, select
else:
    from canonical.swe_kernel.goal_native_probe_v1 import named_symbols, observe, select

def inside(mode):
    sys.path.insert(0, '/input')
    import ranker  # local copy of objective_relevance_bm25.py, no network calls
    repo = Path('/work/repo')
    shutil.copytree('/input/base', repo, symlinks=True)
    goal = Path('/input/goal').read_text()
    result = select(repo, goal, mode == 'broad', ranker)
    result.update(mode=mode, goal_named_symbols=named_symbols(goal), probes=[])
    env = {'PATH': '/usr/bin:/bin', 'HOME': '/tmp', 'LC_ALL': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1',
           'PYTHONPATH': str(repo)}  # isolated venv, use its declared native pytest plugins
    for path in result['selected']:
        row = {'path': path}
        t0 = time.monotonic()
        try:
            p = subprocess.run(['/input/venv/bin/python', '-B', '/input/driver.py', '--observe', path], cwd=repo,
                               env=env, capture_output=True, timeout=15, stdin=subprocess.DEVNULL)
            marker = b'BRAIN_NATIVE_PROBE:'
            if p.returncode == 0 and marker in p.stdout:
                row.update(json.loads(p.stdout.rsplit(marker, 1)[-1]))
                if row['exit'] not in (0, 1):
                    row['error'] = 'INCOMPLETE_TEST_RUN'
                    row['diagnostic'] = (p.stdout.rsplit(marker, 1)[0] + p.stderr).decode(errors='replace')[-600:]
            else:
                row.update(error='NO_OBSERVATION', process_exit=p.returncode,
                           diagnostic=(p.stdout + p.stderr).decode(errors='replace')[-600:])
        except subprocess.TimeoutExpired:
            row.update(error='TIMEOUT')
        row['seconds'] = round(time.monotonic() - t0, 3)
        result['probes'].append(row)
    return result


def compare(base, instruction, venv):
    from canonical.runtime.zero_ambient_namespace_launcher_v1 import run_confined
    from canonical.runtime.bound_capabilities import objective_relevance_bm25 as bm25
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        room = Path(tmp)
        shutil.copytree(base, room / 'base', symlinks=True, ignore=shutil.ignore_patterns('.git', '__pycache__'))
        shutil.copytree(venv, room / 'venv', symlinks=True)
        shutil.copyfile(instruction, room / 'goal')
        shutil.copyfile(bm25.__file__, room / 'ranker.py')
        shutil.copyfile(__file__, room / 'driver.py')
        from canonical.swe_kernel import goal_native_probe_v1
        shutil.copyfile(goal_native_probe_v1.__file__, room / 'goal_native_probe_v1.py')
        for mode in ('selective', 'broad'):
            launch = run_confined({'input_dir': tmp, 'argv': ['/usr/bin/python3', '-I', '-B', '/input/driver.py', '--inside', mode],
                                   'expose_runtime_devices': True, 'limits': {'memory_mb': 2048, 'wallclock_s': 100,
                                   'cpu_seconds': 80, 'pids': 128, 'scratch_mb': 256, 'nofile': 128, 'max_file_mb': 64}})
            payload = launch.pop('broker_payload')
            rows.append({'mode': mode, 'launcher': launch, 'result': json.loads(payload) if payload else None})
    return {'base': subprocess.check_output(['git', '-C', str(base), 'rev-parse', 'HEAD'], text=True).strip(),
            'goal_sha256': hashlib.sha256(instruction.read_bytes()).hexdigest(), 'rows': rows}


if __name__ == '__main__':
    if sys.argv[1:2] == ['--inside']:
        with os.fdopen(int(os.environ['PROJECT_BRAIN_BROKER_FD']), 'wb') as f:
            f.write(json.dumps(inside(sys.argv[2])).encode())
    elif sys.argv[1:2] == ['--observe']:
        print('BRAIN_NATIVE_PROBE:' + json.dumps(observe(sys.argv[2], named_symbols(Path('/input/goal').read_text()))))
    else:
        p = argparse.ArgumentParser(description=__doc__)
        for name in ('base', 'instruction', 'venv'):
            p.add_argument('--' + name, required=True, type=Path)
        a = p.parse_args()
        print(json.dumps(compare(a.base, a.instruction, a.venv), indent=2))

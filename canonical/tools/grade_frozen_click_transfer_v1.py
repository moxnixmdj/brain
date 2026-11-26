"""Evaluate a *frozen* proposal on the historical Click-version control.

Evaluator only. Do not mount this, its inputs, or its output in the producer.
Each arm gets the unchanged receiver suite (upstream defaults) and, separately,
the teacher's one post-fix test file. The latter tests the same requirement,
not a new task. Run in a disposable Linux sandbox with unshare and pytest.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

CHECK = 'tests/test_arguments.py'
CHECK_HASH = '3724b419da2c30f078bf01a07f6f70a4860a92151f44f3968324f3f04bad32da'


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def execute(python: str, wt: Path, check: bool, scratch: Path) -> dict:
    xml = scratch / 'junit.xml'
    cmd = ['unshare', '--user', '--map-current-user', '--net', python, '-m', 'pytest',
           '-q', '--tb=no', '-p', 'no:cacheprovider', f'--junitxml={xml}', CHECK if check else 'tests']
    env = {'HOME': str(scratch), 'PATH': f'{Path(python).parent}:/usr/bin:/bin', 'LC_ALL': 'C.UTF-8',
           'PYTHONHASHSEED': '0', 'PYTHONDONTWRITEBYTECODE': '1', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',
           'PYTHONPATH': str(wt / 'src')}
    start = time.monotonic()
    with (scratch / 'pytest.log').open('wb') as log:
        proc = subprocess.Popen(cmd, cwd=wt, env=env, stdin=subprocess.DEVNULL, stdout=log,
                                stderr=subprocess.STDOUT, start_new_session=True)
        try:
            rc = proc.wait(timeout=120)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
            return {'status': 'TIMEOUT', 'seconds': round(time.monotonic() - start, 3)}
    result = {'exit': rc, 'seconds': round(time.monotonic() - start, 3),
              'log_sha256': sha(scratch / 'pytest.log')}
    if not xml.is_file():
        return {**result, 'status': 'NO_REPORT'}
    cases = {}
    for case in ET.parse(xml).iter('testcase'):
        key = case.get('classname', '') + '::' + case.get('name', '')
        if key in cases:
            raise ValueError(f'duplicate case: {key}')
        skipped = case.find('skipped')
        if skipped is not None and skipped.get('type') == 'pytest.xfail':
            cases[key] = 'xfailed'
        else:
            cases[key] = next((tag for tag in ('failure', 'error', 'skipped') if case.find(tag) is not None), 'passed')
    (scratch / 'verdicts.json').write_text(json.dumps(cases, sort_keys=True))
    status = 'INCOMPLETE' if rc not in (0, 1) else 'RAN' if cases else 'EMPTY_REPORT'
    return {**result, 'status': status,
            'counts': dict(collections.Counter(cases.values())), 'verdicts': cases}


def grade(root: Path, check: Path, frozen: Path, recorded: dict, output: Path, python: str) -> dict:
    if sha(check) != CHECK_HASH:
        raise ValueError('wrong evaluation check')
    output.mkdir(exist_ok=False)
    rows = {}
    baseline = {}
    for arm in ('empty', 'raw_traces', 'generalized'):
        rows[arm] = {}
        info = recorded['arms'][arm]['first_candidate']
        for measurement in ('native', 'teacher_check'):
            scratch = (output / arm / measurement).resolve()
            scratch.mkdir(parents=True)
            with tempfile.TemporaryDirectory(prefix='click-check-') as temp:
                wt = Path(temp) / 'repo'
                shutil.copytree(root, wt, ignore=shutil.ignore_patterns('.git', '__pycache__', '.pytest_cache', '.venv'))
                if info is not None:
                    rel = Path(info['path'])
                    if rel.is_absolute() or '..' in rel.parts or rel.suffix != '.py':
                        raise ValueError('invalid product path')
                    candidate = frozen / arm / rel
                    if sha(candidate) != info['sha256']:
                        raise ValueError('proposal changed after freeze')
                    product = wt / 'src' / 'click' / rel
                    if not product.is_file():
                        raise ValueError('proposal not a replacement of receiver source')
                    shutil.copyfile(candidate, product)
                if measurement == 'teacher_check':
                    shutil.copyfile(check, wt / CHECK)
                r = execute(python, wt, measurement == 'teacher_check', scratch)
            cases = r.pop('verdicts', {})
            if arm == 'empty':
                baseline[measurement] = cases
            old = baseline[measurement]
            r['same_test_names_as_empty'] = bool(cases) and cases.keys() == old.keys()
            r['lost_passes'] = sorted(k for k in old if old[k] == 'passed' and cases.get(k) != 'passed')
            r['failures_to_pass'] = sorted(k for k in old if old[k] in ('failure', 'error') and cases.get(k) == 'passed')
            for key in ('lost_passes', 'failures_to_pass'):
                r[key] = {'count': len(r[key]), 'first_six': r[key][:6]}
            rows[arm][measurement] = r
    return rows


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--checkout', type=Path, required=True, help='clean receiver release archive')
    p.add_argument('--teacher-check', type=Path, required=True, help='the pinned evaluator-only file')
    p.add_argument('--frozen', type=Path, required=True, help='proposal directory for this target')
    p.add_argument('--probe', type=Path, required=True, help='probe result with frozen candidate hashes')
    p.add_argument('--index', type=int, required=True, help='receiver index in probe result')
    p.add_argument('--output', type=Path, required=True, help='new directory for evaluator logs')
    a = p.parse_args()
    report = grade(a.checkout, a.teacher_check, a.frozen, json.loads(a.probe.read_bytes())['targets'][a.index],
                   a.output, sys.executable)
    print(json.dumps(report, indent=2))

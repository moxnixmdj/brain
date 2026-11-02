#!/usr/bin/env python3
"""Compare a supplied historical diagnose-repair snapshot on the same fixtures.

The historical path proposes a patch and runs its own whole-suite gate; this
harness applies its single-file diff to a disposable copy and runs the same
independent finite audit as live_scoped_transfer_benchmark_v1. Historical code
is imported only by a child, never from the current process. The caller must
supply trusted historical source and pytest paths. Tests run without OS
confinement in this harness: only the fixed fixtures below are appropriate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

from canonical.tools import live_scoped_transfer_benchmark_v1 as live
from canonical.tools.shared_skill_transfer_benchmark_v1 import CASES

ROOT = Path(__file__).resolve().parents[2]


def safe_single_file_diff(diff: str) -> bool:
    """Accept only a normal unified diff whose sole target is subject.py."""
    headers = [line for line in diff.splitlines() if line.startswith(('--- ', '+++ '))]
    return headers == ['--- a/subject.py', '+++ b/subject.py']


def run_historical(snapshot: Path, pytest_path: Path, base: Path, name: str) -> dict:
    source, meaning = CASES[name]
    case = base / name
    case.mkdir()
    project = case / 'project'
    live.project(project, source, meaning)
    before_source = (project / 'subject.py').read_bytes()
    before_test = (project / 'test_subject.py').read_bytes()
    args = {'source_root': 'project', 'source_path': 'project/subject.py',
            'test_paths': ['project/test_subject.py'], 'output_path': 'reports/result.json',
            'deadline_s': 40, 'workers': 1, 'max_candidates': 100,
            'confine': 'off', 'review': 'off'}
    child = ('import json,sys\n'
             'from canonical.runtime.bound_capabilities import software_diagnose_then_repair_v1 as d\n'
             'print(json.dumps(d.run(json.loads(sys.argv[1]),sys.argv[2])))\n')
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
               PYTHONPATH=os.pathsep.join((str(snapshot), str(pytest_path))))
    started = time.perf_counter()
    try:
        proc = subprocess.run([sys.executable, '-c', child, json.dumps(args), str(case)],
                              cwd=snapshot, env=env, capture_output=True, text=True, timeout=55)
    except subprocess.TimeoutExpired:
        return {'case': name, 'status': 'HARNESS_TIMEOUT', 'verified': False,
                'audit_pass': False, 'elapsed_ms': round((time.perf_counter()-started)*1000, 3)}
    elapsed = round((time.perf_counter() - started) * 1000, 3)
    row = {'case': name, 'negative_control': meaning == 'inclusive', 'elapsed_ms': elapsed,
           'worker_returncode': proc.returncode,
           'source_unchanged': (project / 'subject.py').read_bytes() == before_source,
           'tests_unchanged': (project / 'test_subject.py').read_bytes() == before_test,
           'audit_pass': False}
    try:
        result = json.loads(proc.stdout) if proc.returncode == 0 else {}
    except json.JSONDecodeError:
        result = {}
    row.update(status=result.get('status', 'WORKER_ERROR'), verified=result.get('verified') is True,
               gate=result.get('gate'), confined=result.get('confined'),
               stderr_tail=proc.stderr[-1200:] if not result else '')
    if meaning == 'inclusive' and not row['verified']:
        row['audit_pass'] = live.audit(project, meaning)
        row['negative_handled'] = row['audit_pass'] and row['source_unchanged'] and row['tests_unchanged']
    diff_name = result.get('diff_path')
    if result.get('verified') and isinstance(diff_name, str):
        diff_file = (case / diff_name).resolve()
        if case.resolve() not in diff_file.parents or not diff_file.is_file():
            row['audit_error'] = 'DIFF_OUTSIDE_CASE'
            return row
        diff = diff_file.read_text()
        if not safe_single_file_diff(diff):
            row['audit_error'] = 'UNEXPECTED_DIFF_TARGETS'
            return row
        audit_dir = case / 'independent_audit'
        shutil.copytree(project, audit_dir)
        patch = subprocess.run(['git', 'apply', '--check', str(diff_file)], cwd=audit_dir,
                               capture_output=True, timeout=10)
        if patch.returncode == 0:
            patch = subprocess.run(['git', 'apply', str(diff_file)], cwd=audit_dir,
                                   capture_output=True, timeout=10)
        if patch.returncode == 0:
            row['audit_pass'] = live.audit(audit_dir, meaning)
        else:
            row['audit_error'] = 'DIFF_APPLY_FAILED'
    return row


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--branch-source', type=Path, required=True)
    p.add_argument('--pytest-path', type=Path, required=True)
    p.add_argument('--only', choices=tuple(CASES))
    args = p.parse_args()
    snapshot, pytest_path = args.branch_source.resolve(), args.pytest_path.resolve()
    module = snapshot / 'canonical/runtime/bound_capabilities/software_diagnose_then_repair_v1.py'
    if not module.is_file() or not (pytest_path / 'pytest').is_dir():
        p.error('source snapshot and pytest installation required')
    with tempfile.TemporaryDirectory(prefix='brain_branch_repair_') as td:
        base = Path(td)
        historical = [run_historical(snapshot, pytest_path, base, name)
                      for name in ([args.only] if args.only else CASES)]
    print(json.dumps({'schema': 'BRAIN_DIAGNOSE_BRANCH_COMPARISON_V1',
                      'scope': 'known fixed boundary cases; one historical cold search, not a transfer comparison',
                      'historical_module_sha256': hashlib.sha256(module.read_bytes()).hexdigest(),
                      'historical': historical}, indent=2))


if __name__ == '__main__':
    main()

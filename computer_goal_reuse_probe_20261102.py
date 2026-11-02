#!/usr/bin/env python3
"""Measure an ordinary file goal versus the existing learned-tool path.

Each call runs in a new interpreter with a network namespace, only gzip on PATH,
and state and files inside a disposable copy. This is not a filesystem or hostile
code sandbox: run only a trusted checkout. The cold direct arm starts with an
empty transfer store, but discover() has no learning-off switch and may write new
memory during that run. The fabric and direct routes differ and are not a fair
head-to-head comparison or evidence of general computer use.

Run: python3 computer_goal_reuse_probe_20261102.py
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent
WORKER = r'''
import json, os, sys, time
from pathlib import Path
from canonical.runtime.unified_cognitive_fabric_v1 import run
from canonical.runtime.computer_env_v1 import perform
mode, role, root_arg, r3_arg = sys.argv[1:]
work = Path(root_arg)
name = 'lesson.txt' if role == 'teach' else 'report.txt'
goal = 'compress ' + name + ' into ' + name + '.gz'
start = time.monotonic()
if mode == 'fabric':
    result = run({'mode': 'RAW_GOAL',
                  'payload': {'task_id': 'file-' + role, 'goal': goal, 'cwd': str(work)},
                  'options': {'state_path': r3_arg, 'learn': role != 'cold',
                              'auto_repair': False}})
    result = result.get('result') or {}
    live = result.get('_live_runtime') or {}
    learning = live.get('learning') or {}
    compact = {'pass': result.get('pass'), 'status': result.get('status'),
               'reason': result.get('reason'),
               'semantic_acceptance_complete': result.get('semantic_acceptance_complete'),
               'selected_capability': result.get('compiled_capability_id'),
               'refused_capability': result.get('refused_capability'),
               'learning_status': learning.get('status'),
               'permanent_reuse_authorized': learning.get('permanent_reuse_authorized'),
               'reused_skill_id': live.get('reused_skill_id')}
else:
    result = perform(goal, cwd=work)
    compact = {k: result.get(k) for k in ('pass', 'status', 'learned_by',
                                            'from_memory', 'plan', 'verification',
                                            'source_content_verified')}
print(json.dumps({'pid': os.getpid(), 'elapsed_s': round(time.monotonic() - start, 6),
                  'goal': goal, 'result': compact}, default=str))
'''


def digest(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def run() -> dict:
    gzip_bin = shutil.which('gzip')
    unshare = shutil.which('unshare')
    if not gzip_bin or not unshare:
        raise RuntimeError('GNU gzip and Linux unshare are required; no unrestricted fallback')
    with tempfile.TemporaryDirectory(prefix='brain_real_file_probe_') as temporary:
        base = Path(temporary)
        tree = base / 'tree'
        shutil.copytree(ROOT, tree, ignore=shutil.ignore_patterns(
            '.git', '__pycache__', '.pytest_cache', '*.pyc', 'tmp', '.venv', 'node_modules'))
        bin_dir = base / 'bin'
        bin_dir.mkdir()
        (bin_dir / 'gzip').symlink_to(Path(gzip_bin).resolve())
        test_root = tree / 'canonical/astra_runtime/tmp/real_file_probe'
        test_root.mkdir(parents=True)
        r3_state = test_root / 'r3.json'
        common_env = {k: v for k, v in os.environ.items() if not k.startswith('BRAIN_')}
        common_env.update(PATH=str(bin_dir), PYTHONPATH=str(tree), PYTHONDONTWRITEBYTECODE='1')
        rows = []
        for mode, role in [('fabric', 'teach'), ('fabric', 'cold'), ('fabric', 'warm'),
                           ('direct', 'teach'), ('direct', 'cold'), ('direct', 'warm'),
                           ('direct', 'missing')]:
            work = test_root / (mode + '_' + role)
            work.mkdir()
            state = test_root / ('state_' + mode + '_' + role)
            if mode == 'direct' and role == 'warm':
                shutil.copytree(test_root / 'state_direct_teach', state)
            else:
                state.mkdir()
            name = 'lesson.txt' if role == 'teach' else 'report.txt'
            source = work / name
            expected = b'first teaching file\n' * 5 if role == 'teach' else b'different target\nline two\n' * 4
            if role != 'missing':
                source.write_bytes(expected)
            sentinel = work / '_verify.py'
            sentinel.write_bytes(b'existing user file; do not modify\n')
            before_source = digest(source)
            before_sentinel = digest(sentinel)
            env = dict(common_env, BRAIN_STATE_DIR=str(state),
                       BRAIN_TRANSFER_LEARNING_STATE=str(state / 'episodes.json'))
            child = subprocess.run([unshare, '--user', '--map-root-user', '--net',
                                    sys.executable, '-c', WORKER, mode, role,
                                    str(work), str(r3_state)],
                                   cwd=tree, env=env, text=True, capture_output=True,
                                   timeout=90, check=True)
            result = json.loads(child.stdout)
            target = work / (name + '.gz')
            try:
                actual = gzip.decompress(target.read_bytes()) if target.is_file() else None
                outcome_correct = actual is not None and actual == expected and role != 'missing'
            except (OSError, EOFError):
                outcome_correct = False
            result.update(mode=mode, role=role, target_exists=target.is_file(),
                          full_decompression_matches_input=outcome_correct,
                          source_unchanged=before_source == digest(source),
                          neighboring_file_unchanged=before_sentinel == digest(sentinel))
            rows.append(result)
        archives = sorted(x.name for x in (tree / 'canonical/astra_runtime/tmp').glob('brain_out__*.tar.gz'))
        return {'scope': 'single gzip file goal, restricted PATH and synthetic file inputs',
                'independent_personnel_verification': False,
                'cold_direct_control': 'empty initial transfer store, not learning disabled',
                'source_and_state_isolation': 'disposable checkout; network namespace; not a filesystem sandbox',
                'unexpected_generated_archive_names': archives, 'rows': rows}


def main() -> None:
    start = time.monotonic()
    result = run()
    result['total_wall_s'] = round(time.monotonic() - start, 3)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

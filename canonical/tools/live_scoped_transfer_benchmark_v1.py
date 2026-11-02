#!/usr/bin/env python3
"""Small, non-blind live-repair comparison, not an arbitrary-task benchmark.

A single verified boundary lesson is stored once. Each arm runs in a fresh
interpreter on an identical independent copy of each known constructed target.
The cold arm still has the production fallback search. The external audit is
separate from the visible acceptance suite. Only temporary files are modified.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time

from canonical.tools.shared_skill_transfer_benchmark_v1 import CASES, TEACH_BEFORE, TEACH_AFTER

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = {'schema_version': 1, 'scope_id': 'benchmark/exclusive-boundary/v1',
            'verification_kind': 'TEST_SUITE', 'dependencies': {'protocol': '1'},
            'preconditions': {'role': 'boundary'}}
CONTEXT = {k: CONTRACT[k] for k in ('dependencies', 'preconditions')}
EXPRESSIONS = {'exclusive': 'x < hi', 'nonnegative_exclusive': 'x >= 0 and x < hi',
               'inclusive': 'x <= hi'}


def project(root: Path, source: str, meaning: str, function: str = 'target') -> None:
    root.mkdir(parents=True)
    (root / 'subject.py').write_text(source)
    (root / 'test_subject.py').write_text(
        'import unittest\nfrom subject import ' + function + '\n'
        'class Checks(unittest.TestCase):\n'
        ' def test_boundary(self):\n'
        '  for x, hi in [(-2,-2),(-1,0),(0,0),(0,3),(3,3),(4,3)]:\n'
        '   self.assertEqual(' + function + '(x, hi), ' + EXPRESSIONS[meaning] + ')\n')


def teach(base: Path) -> dict:
    from canonical.swe_kernel.skill_verification_contract_v1 import ProjectTestOracle
    from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore
    train = base / 'training'
    project(train, TEACH_BEFORE, 'exclusive', 'within')
    store = VerifiedSkillStore(base / 'skills.sqlite', seed=False)
    start = time.perf_counter()
    result = store.crystallize_code_fix(before_snippet=TEACH_BEFORE, after_snippet=TEACH_AFTER,
        language='python', contract=CONTRACT,
        training_verifier=ProjectTestOracle(train, 'subject.py', ['test_subject.py'], CONTRACT['scope_id']))
    return {'admitted': result.get('crystallized') is True,
            'elapsed_ms': round(1000 * (time.perf_counter() - start), 3)}


def audit(root: Path, meaning: str) -> bool:
    # A new interpreter, separate from both the repair and its visible tests.
    code = ('import sys\nsys.path.insert(0,sys.argv[1])\nfrom subject import target\n'
            'for x in range(-20,21):\n for hi in range(-20,21):\n'
            '  assert target(x, hi) == (' + EXPRESSIONS[meaning] + ')\n')
    return subprocess.run([sys.executable, '-c', code, str(root)], capture_output=True,
                          timeout=20, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1')).returncode == 0


def worker(base: Path, arm: str) -> dict:
    from canonical.runtime.bound_capabilities import python_repair_apply_verified_v1 as apply
    rows = []
    for name, (source, meaning) in CASES.items():
        rel = Path(arm) / name
        target = base / rel
        project(target, source, meaning)
        tests_before = (target / 'test_subject.py').read_bytes()
        # Fallback search can teach on success. Give every case its own snapshot
        # of the source-only lesson so earlier targets cannot contaminate later ones.
        db_path = rel.parent / (name + '.sqlite')
        with sqlite3.connect(base / 'skills.sqlite') as src, sqlite3.connect(base / db_path) as dest:
            src.backup(dest)
        config = {'enabled': arm != 'cold', 'db_path': db_path.as_posix(),
                  'target_path': (rel / 'subject.py').as_posix(), 'contract': CONTRACT,
                  'context': CONTEXT, 'allow_operator_generalization': arm == 'generalized'}
        args = {'source_root': rel.as_posix(), 'test_paths': [(rel / 'test_subject.py').as_posix()],
                'output_path': (Path('reports') / (arm + '_' + name + '.json')).as_posix(),
                'timeout_s': 20, 'max_guided_files': 1, 'max_guided_symbols_per_file': 2,
                'mutations_per_file': 12, 'max_pair_candidates': 24, 'retained_learning': config}
        start = time.perf_counter()
        result = apply.run(args, base)
        elapsed = 1000 * (time.perf_counter() - start)
        retained = result.get('retained_learning', {})
        rows.append({'case': name, 'negative_control': meaning == 'inclusive',
                     'pass': result.get('pass') is True, 'applied': result.get('applied') is True,
                     'already_satisfied': result.get('already_satisfied') is True,
                     'retained_hit': retained.get('hit') is True,
                     'recall_strategy': retained.get('recall_strategy'),
                     'oracle_calls': retained.get('oracle_calls', 0),
                     'search_invocations': result.get('repair_search_invocations', 0),
                     'audit_pass': audit(target, meaning),
                     'tests_unchanged': (target / 'test_subject.py').read_bytes() == tests_before,
                     'elapsed_ms': round(elapsed, 3)})
    return {'arm': arm, 'pid': os.getpid(), 'cases': rows}


def main() -> None:
    if len(sys.argv) == 4 and sys.argv[1] == '--worker':
        if sys.argv[3] not in ('cold', 'statement', 'generalized'):
            raise SystemExit('UNKNOWN_ARM')
        print(json.dumps(worker(Path(sys.argv[2]), sys.argv[3])))
        return
    if len(sys.argv) != 1:
        raise SystemExit('usage: python -m canonical.tools.live_scoped_transfer_benchmark_v1')
    with tempfile.TemporaryDirectory(prefix='brain_live_transfer_') as tmp:
        base = Path(tmp)
        lesson = teach(base)
        if not lesson['admitted']:
            raise RuntimeError('LESSON_NOT_ADMITTED')
        arms = []
        for arm in ('cold', 'statement', 'generalized'):
            proc = subprocess.run([sys.executable, '-m', 'canonical.tools.live_scoped_transfer_benchmark_v1',
                                   '--worker', str(base), arm], cwd=ROOT, capture_output=True,
                                  text=True, check=True, timeout=180,
                                  env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
            arms.append(json.loads(proc.stdout))
        print(json.dumps({'schema': 'BRAIN_LIVE_SCOPED_TRANSFER_BENCHMARK_V1',
                          'scope': 'known constructed boundary variants, non-blind; independent finite audit',
                          'lesson': lesson, 'arms': arms}, indent=2))


if __name__ == '__main__':
    main()

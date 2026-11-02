"""Regression for a small comparison of actual live repair arms."""
import json
import os
from pathlib import Path
import subprocess
import sys

from canonical.tools.shared_skill_transfer_benchmark_v1 import CASES

ROOT = Path(__file__).resolve().parents[2]


def test_live_comparison_reopens_store_uses_fallback_and_separate_audit(tmp_path):
    caller_db = tmp_path / 'caller.sqlite'
    caller_db.write_bytes(b'caller owned')
    env = dict(os.environ, BRAIN_SKILL_STORE_PATH=str(caller_db))
    p = subprocess.run([sys.executable, '-m', 'canonical.tools.live_scoped_transfer_benchmark_v1'],
                       cwd=ROOT, env=env, text=True, capture_output=True, check=True, timeout=180)
    assert caller_db.read_bytes() == b'caller owned'
    report = json.loads(p.stdout)
    assert report['lesson']['admitted']
    arms = {arm['arm']: arm for arm in report['arms']}
    assert set(arms) == {'cold', 'statement', 'generalized'}
    assert len({arm['pid'] for arm in arms.values()}) == 3
    for arm in arms.values():
        assert {r['case'] for r in arm['cases']} == set(CASES)
        for row in arm['cases']:
            assert row['tests_unchanged']
            if row['pass']:
                assert row['audit_pass'], row
        negative = next(r for r in arm['cases'] if r['negative_control'])
        assert negative['already_satisfied'] and not negative['applied'] and not negative['retained_hit']
    cold = {r['case']: r for r in arms['cold']['cases']}
    statement = {r['case']: r for r in arms['statement']['cases']}
    generalized = {r['case']: r for r in arms['generalized']['cases']}
    assert all(cold[name]['search_invocations'] == 1 for name in CASES if name != 'negative_inclusive')
    assert statement['renamed']['retained_hit']
    assert not statement['disjunction']['retained_hit']
    for name in CASES:
        if name != 'negative_inclusive':
            assert generalized[name]['retained_hit'] and generalized[name]['audit_pass']
            assert generalized[name]['search_invocations'] == 0

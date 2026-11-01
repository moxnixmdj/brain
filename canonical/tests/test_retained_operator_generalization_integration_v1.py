"""Opt-in generalized recall through the real scoped repair boundary."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from canonical.swe_kernel.skill_verification_contract_v1 import ProjectTestOracle
from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = {'schema_version': 1, 'scope_id': 'boundary/integration/v1',
            'verification_kind': 'TEST_SUITE', 'dependencies': {'protocol': '1'},
            'preconditions': {'role': 'exclusive-upper-bound'}}
CONTEXT = {k: CONTRACT[k] for k in ('dependencies', 'preconditions')}
BEFORE = 'def within(x, hi):\n    return x <= hi\n'
AFTER = 'def within(x, hi):\n    return x < hi\n'
TARGET = 'def within(x, hi):\n    return x < hi or x == hi\n'


def project(path, source, inclusive=False):
    path.mkdir()
    (path / 'm.py').write_text(source)
    cmp = '<=' if inclusive else '<'
    (path / 'test_m.py').write_text(
        'import unittest\nfrom m import within\nclass Checks(unittest.TestCase):\n'
        ' def test_values(self):\n'
        '  for x, hi in [(-1,0),(0,0),(2,1),(3,3)]:\n'
        f'   self.assertEqual(within(x, hi), x {cmp} hi)\n')


@pytest.fixture
def lesson(tmp_path):
    train = tmp_path / 'train'
    project(train, BEFORE)
    db = tmp_path / 'memory.sqlite'
    store = VerifiedSkillStore(db, seed=False)
    result = store.crystallize_code_fix(before_snippet=BEFORE, after_snippet=AFTER,
        language='python', contract=CONTRACT,
        training_verifier=ProjectTestOracle(train, 'm.py', ['test_m.py'], CONTRACT['scope_id']))
    assert result['crystallized'], result
    return db, result['skill_id']


def recall(store, oracle, **overrides):
    args = dict(source_text=TARGET, language='python', verifier=oracle,
                required_verification_kind='TEST_SUITE', scope_id=CONTRACT['scope_id'],
                context=CONTEXT, allow_operator_generalization=True)
    args.update(overrides)
    return store.recall_and_apply_verified(**args)


def test_opt_in_reopens_store_and_applies_through_live_repair_with_external_audit(tmp_path, lesson):
    db, _ = lesson
    target = tmp_path / 'target'
    project(target, TARGET)
    args = {'source_root': 'target', 'test_paths': ['target/test_m.py'],
            'output_path': 'report.json', 'timeout_s': 20,
            'retained_learning': {'enabled': True, 'target_path': 'target/m.py',
                'db_path': db.name, 'contract': CONTRACT, 'context': CONTEXT,
                'allow_operator_generalization': True}}
    child = ('import json,sys\n'
             'from canonical.runtime.bound_capabilities import python_repair_apply_verified_v1 as a\n'
             'print(json.dumps(a.run(json.loads(sys.argv[1]),sys.argv[2])))\n')
    env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONDONTWRITEBYTECODE='1')
    proc = subprocess.run([sys.executable, '-c', child, json.dumps(args), str(tmp_path)],
                          cwd=ROOT, env=env, text=True, capture_output=True, timeout=90, check=True)
    result = json.loads(proc.stdout)
    assert result['pass'] and result['applied'], result
    assert result['repair_search_invocations'] == 0, result
    assert result['retained_learning']['hit']
    assert result['retained_learning']['recall_strategy'] == 'operator_generalization'
    assert result['retained_learning']['verification']['kind'] == 'TEST_SUITE'
    # A separate interpreter audits inputs not in the visible project suite.
    audit = ('import sys; sys.path.insert(0,sys.argv[1]); from m import within\n'
             'assert all(within(x,h) == (x<h) for x in range(-20,21) for h in range(-20,21))\n')
    subprocess.run([sys.executable, '-c', audit, str(target)], env=env, check=True, timeout=20)


def test_disabled_scope_and_typed_verifier_controls(tmp_path, lesson):
    db, _ = lesson
    target = tmp_path / 'target'
    project(target, TARGET)
    oracle = ProjectTestOracle(target, 'm.py', ['test_m.py'], CONTRACT['scope_id'])
    store = VerifiedSkillStore(db, seed=False)
    assert recall(store, oracle, allow_operator_generalization=False) is None
    assert recall(store, oracle, context={'dependencies': {'protocol': 'wrong'}, 'preconditions': CONTEXT['preconditions']}) is None
    assert recall(store, lambda _: True) is None
    with pytest.raises(ValueError, match='REQUIRES_SCOPED'):
        recall(store, lambda _: True, required_verification_kind='CALLER_PREDICATE')
    with pytest.raises(ValueError, match='INVALID_OPERATOR'):
        recall(store, oracle, allow_operator_generalization='true')


def test_inclusive_negative_and_concurrent_invalidation(tmp_path, lesson):
    db, skill_id = lesson
    target = tmp_path / 'target'
    project(target, TARGET, inclusive=True)
    store = VerifiedSkillStore(db, seed=False)
    oracle = ProjectTestOracle(target, 'm.py', ['test_m.py'], CONTRACT['scope_id'])
    assert recall(store, oracle) is None
    (target / 'test_m.py').unlink()
    (target / 'm.py').unlink()
    target.rmdir()
    project(target, TARGET)
    oracle = ProjectTestOracle(target, 'm.py', ['test_m.py'], CONTRACT['scope_id'])
    def revoke_after_test(candidate):
        result = oracle(candidate)
        if result.passed:
            assert VerifiedSkillStore(db, seed=False).invalidate(skill_id, 'counterexample')
        return result
    assert recall(store, revoke_after_test) is None

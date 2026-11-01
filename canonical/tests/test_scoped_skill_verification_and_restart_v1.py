"""Bounded retained-repair qualification, not a universal learning benchmark.

All fixtures run real project tests through the maintained copied-tree runner.
Fresh interpreters exercise storage/recall; no import or filesystem substitution.
The no-learning route deliberately has no independent fallback repair algorithm.
"""
from __future__ import annotations

import ast
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from canonical.swe_kernel.skill_verification_contract_v1 import (
    ProjectTestOracle, VerificationResult, evaluate, source_sha256,
)
from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore

ROOT = Path(__file__).resolve().parents[2]
SCOPE = 'sum-two-monetary-amounts/v1'
CONTRACT = {'schema_version': 1, 'scope_id': SCOPE, 'verification_kind': 'TEST_SUITE',
            'dependencies': {'operation_protocol': '1', 'python_major': sys.version_info.major},
            'preconditions': {'target_role': 'sum_two_amounts'}}
CONTEXT = {key: CONTRACT[key] for key in ('dependencies', 'preconditions')}


def project(root: Path, *, held_out: bool = False):
    root.mkdir()
    package = 'workshop' if held_out else 'ledger'
    folder = root / package
    folder.mkdir()
    (folder / '__init__.py').write_text('')
    if held_out:
        target = 'workshop/pricing.py'
        before = 'def sum_costs(material, labor):\n    return material - labor\n'
        (folder / 'invoice.py').write_text(
            'from .pricing import sum_costs\n'
            'def quote(items, fee):\n'
            '    base = sum(price * count for price, count in items)\n'
            '    return sum_costs(base, fee)\n')
        tests = (
            'import unittest\nfrom workshop.invoice import quote\n'
            'class BillingTests(unittest.TestCase):\n'
            ' def test_multiple_lines(self): self.assertEqual(quote([(3,4),(2,5)],7),29)\n'
            ' def test_zero_fee(self): self.assertEqual(quote([(6,2)],0),12)\n'
            ' def test_credit(self): self.assertEqual(quote([(5,3)],-4),11)\n')
    else:
        target = 'ledger/math_ops.py'
        before = 'def combine(left, right):\n    return left - right\n'
        (folder / 'api.py').write_text(
            'from .math_ops import combine\n'
            'def total(lines):\n'
            '    accumulated = 0\n'
            '    for line in lines:\n'
            '        accumulated = combine(accumulated, line)\n'
            '    return accumulated\n')
        tests = (
            'import unittest\nfrom ledger.api import total\n'
            'class LedgerTests(unittest.TestCase):\n'
            ' def test_sum(self): self.assertEqual(total([2,3,4]),9)\n'
            ' def test_empty(self): self.assertEqual(total([]),0)\n'
            ' def test_signed(self): self.assertEqual(total([8,-2]),6)\n')
    (root / target).write_text(before)
    (root / 'test_behavior.py').write_text(tests)
    (root / 'skill_context.json').write_text(json.dumps(CONTEXT))
    return target, before, before.replace(' - ', ' + ')


def snapshot(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}


@pytest.fixture
def lesson(tmp_path):
    root = tmp_path / 'training'
    target, before, after = project(root)
    oracle = ProjectTestOracle(root, target, ['test_behavior.py'], SCOPE)
    store = VerifiedSkillStore(tmp_path / 'skills.sqlite', seed=False)
    result = store.crystallize_code_fix(before_snippet=before, after_snippet=after, language='python',
                                        contract=CONTRACT, training_verifier=oracle)
    assert result['crystallized'], result
    assert result['training_verification']['kind'] == 'TEST_SUITE'
    return store, oracle, before, after, result


def recall(store, source, verifier, **kwargs):
    args = dict(source_text=source, language='python', verifier=verifier,
                scope_id=SCOPE, context=CONTEXT, required_verification_kind='TEST_SUITE')
    args.update(kwargs)
    return store.recall_and_apply_verified(**args)


def test_parse_only_wrong_lesson_never_obtains_behavioral_assurance(tmp_path):
    root = tmp_path / 'training'
    target, before, after = project(root)
    wrong = after.replace(' + ', ' * ')
    store = VerifiedSkillStore(tmp_path / 'skills.sqlite', seed=False)
    taught = store.crystallize_code_fix(before_snippet=before, after_snippet=wrong, language='python',
                                        twin_oracle=lambda s: bool(ast.parse(s)))
    assert taught['crystallized']
    assert taught['training_verification']['kind'] == 'NOT_VERIFIED'
    assert taught['twin_verification']['kind'] == 'CALLER_PREDICATE'
    weak = store.recall_and_apply_verified(source_text=before, language='python',
                                           verifier=lambda s: bool(ast.parse(s)))
    assert weak['verification']['kind'] == 'CALLER_PREDICATE'
    assert weak['whole_task_correctness_proved'] is False
    values = {}
    exec(weak['patched_source'], values)
    assert values['combine'](2, 3) == 6  # the deliberately wrong negative control
    assert recall(store, before, lambda _: True) is None
    oracle = ProjectTestOracle(root, target, ['test_behavior.py'], SCOPE)
    assert recall(store, before, oracle) is None  # legacy record is unscoped
    rejected = store.crystallize_code_fix(before_snippet=before, after_snippet=wrong, language='python',
                                          contract=CONTRACT, training_verifier=oracle)
    assert rejected == {'crystallized': False, 'reason': 'TRAINING_VERIFICATION_FAILED'}


@pytest.mark.parametrize('mutation', [
    'bool', 'truthy_dict', 'syntax', 'compilation', 'bad_hash', 'bad_scope',
    'zero_tests', 'failed', 'failed_returncode', 'bool_returncode', 'missing_program',
])
def test_strict_verification_binds_candidate_scope_kind_and_nonempty_evidence(lesson, mutation):
    store, oracle, before, after, _ = lesson
    measured = oracle(after)
    assert measured.passed
    value = measured
    if mutation == 'bool': value = True
    if mutation == 'truthy_dict': value = {'passed': True, 'kind': 'TEST_SUITE'}
    if mutation == 'syntax': value = replace(measured, kind='SYNTAX')
    if mutation == 'compilation': value = replace(measured, kind='COMPILATION')
    if mutation == 'bad_hash': value = replace(measured, candidate_sha256='0' * 64)
    if mutation == 'bad_scope': value = replace(measured, scope_id='different-operation/v1')
    if mutation == 'zero_tests': value = replace(measured, evidence={**measured.evidence, 'test_count': 0})
    if mutation == 'failed': value = replace(measured, passed=False)
    if mutation == 'failed_returncode': value = replace(measured, evidence={**measured.evidence, 'returncode': 1})
    if mutation == 'bool_returncode': value = replace(measured, evidence={**measured.evidence, 'returncode': False})
    if mutation == 'missing_program': value = replace(measured, evidence={**measured.evidence, 'measurement_program_sha256': ''})
    assert recall(store, before, lambda _: value) is None


def test_real_compilation_has_compilation_only_assurance():
    candidate = 'int main() { return 0; }\n'
    import shutil
    compiler = shutil.which('g++')
    if compiler is None:
        pytest.skip('g++ unavailable; no compilation claim')
    proc = subprocess.run([compiler, '-x', 'c++', '-fsyntax-only', '-'], input=candidate,
                          text=True, capture_output=True, timeout=15)
    result = VerificationResult(proc.returncode == 0, 'COMPILATION', source_sha256(candidate),
                                evidence={'compiler': compiler, 'returncode': proc.returncode})
    assert evaluate(lambda _: result, candidate, 'COMPILATION')['kind'] == 'COMPILATION'
    assert evaluate(lambda _: result, candidate, 'TEST_SUITE') is None


@pytest.mark.parametrize('change', ['scope', 'dependency', 'missing_dependency', 'precondition', 'typed_precondition'])
def test_applicability_refuses_before_running_oracle(lesson, change):
    store, oracle, before, _, _ = lesson
    context = json.loads(json.dumps(CONTEXT))
    scope = SCOPE
    if change == 'scope': scope = 'subtract-amounts/v1'
    if change == 'dependency': context['dependencies']['operation_protocol'] = '2'
    if change == 'missing_dependency': del context['dependencies']['python_major']
    if change == 'precondition': context['preconditions']['target_role'] = 'subtract_amounts'
    if change == 'typed_precondition': context['dependencies']['python_major'] = str(sys.version_info.major)
    calls = oracle.calls
    assert recall(store, before, oracle, scope_id=scope, context=context) is None
    assert oracle.calls == calls


def test_contract_is_in_skill_identity_and_lookup_cannot_mutate_cache(lesson):
    store, oracle, before, after, result = lesson
    other = {**CONTRACT, 'scope_id': 'another-scope/v1'}
    other_oracle = ProjectTestOracle(oracle.root, oracle.target_path, oracle.test_paths, other['scope_id'])
    result2 = store.crystallize_code_fix(before_snippet=before, after_snippet=after, language='python',
                                         contract=other, training_verifier=other_oracle)
    assert result2['crystallized']
    assert result2['skill_id'] != result['skill_id']
    assert store.count() == 2
    records = store.lookup_rules('python')
    records[0]['contract']['scope_id'] = 'tampered'
    records[0]['pattern_tokens'].clear()
    assert all(r['contract']['scope_id'] != 'tampered' for r in store.lookup_rules('python'))
    assert recall(store, before, oracle)['patched_source'] == after


def test_invalidation_survives_restart_and_duplicate_teaching(lesson):
    store, oracle, before, after, result = lesson
    store.lookup_rules('python')  # warm cache in this interpreter
    script = ('from pathlib import Path; import sys; '
              'from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore; '
              'assert VerifiedSkillStore(Path(sys.argv[1]), seed=False).invalidate(sys.argv[2], "counterexample", '
              'counterexample_sha256="a"*64)')
    proc = subprocess.run([sys.executable, '-c', script, str(store.db_path), result['skill_id']],
                          cwd=ROOT, text=True, capture_output=True, timeout=20)
    assert proc.returncode == 0, proc.stderr
    assert recall(store, before, oracle) is None
    assert store.lookup_rules('python')[0]['counterexamples'][0]['reason'] == 'counterexample'
    duplicate = store.crystallize_code_fix(before_snippet=before, after_snippet=after, language='python',
                                           contract=CONTRACT, training_verifier=oracle)
    assert duplicate['state'] == 'INVALIDATED'
    assert store.count() == 1
    assert recall(VerifiedSkillStore(store.db_path, seed=False), before, oracle) is None


def test_invalidation_during_verification_refuses_return(lesson):
    store, oracle, before, _, result = lesson
    def invalidate_then_check(candidate):
        assert VerifiedSkillStore(store.db_path, seed=False).invalidate(result['skill_id'], 'new counterexample')
        return oracle(candidate)
    assert recall(store, before, invalidate_then_check) is None


def test_external_sqlite_deletion_and_restore_refresh_warm_cache(lesson):
    store, oracle, before, _, _ = lesson
    assert len(store.lookup_rules('python')) == 1
    with sqlite3.connect(store.db_path) as conn:
        row = conn.execute('SELECT * FROM crystallized_skills').fetchone()
        conn.execute('DELETE FROM crystallized_skills')
    assert store.lookup_rules('python') == []
    assert recall(store, before, oracle) is None
    with sqlite3.connect(store.db_path) as conn:
        conn.execute('INSERT INTO crystallized_skills VALUES (' + ','.join('?' for _ in row) + ')', row)
    assert recall(store, before, oracle) is not None


def test_empty_or_all_skipped_suite_never_establishes_behavioral_success(tmp_path):
    root = tmp_path / 'empty'
    root.mkdir()
    (root / 'calc.py').write_text('def add(a,b): return a+b\n')
    (root / 'test_behavior.py').write_text('import unittest\n')
    oracle = ProjectTestOracle(root, 'calc.py', ['test_behavior.py'], SCOPE)
    candidate = (root / 'calc.py').read_text()
    assert oracle(candidate).passed is False
    (root / 'test_behavior.py').write_text(
        'import unittest\n@unittest.skip("not implemented")\n'
        'class Tests(unittest.TestCase):\n def test_nothing(self): self.fail()\n')
    assert oracle(candidate).passed is False


def test_oracle_refuses_test_rewrite_and_symlink_tree(tmp_path):
    root = tmp_path / 'project'
    target, before, _ = project(root)
    with pytest.raises(ValueError, match='MUST_NOT_REWRITE_ITS_TESTS'):
        ProjectTestOracle(root, 'test_behavior.py', ['test_behavior.py'], SCOPE)
    (root / 'escape.py').symlink_to(tmp_path / 'outside.py')
    oracle = ProjectTestOracle(root, target, ['test_behavior.py'], SCOPE)
    measured = oracle(before)
    assert measured.passed is False
    assert measured.evidence['error'] == 'MeasurementError'


CHILD = r'''
import json, os, sys
from pathlib import Path
from dataclasses import asdict
from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore
from canonical.swe_kernel.skill_verification_contract_v1 import ProjectTestOracle
mode, db, root, target, scope, contract_json = sys.argv[1:]
root = Path(root)
contract = json.loads(contract_json)
context = json.loads((root / 'skill_context.json').read_text())
store = VerifiedSkillStore(Path(db), seed=False)
oracle = ProjectTestOracle(root, target, ['test_behavior.py'], scope)
before = (root / target).read_text()
if mode == 'teach':
    result = store.crystallize_code_fix(before_snippet=before, after_snippet=before.replace(' - ', ' + '),
               language='python', contract=contract, training_verifier=oracle)
elif mode == 'baseline':
    result = asdict(oracle(before))
elif mode == 'disabled':
    result = None
else:
    result = store.recall_and_apply_verified(source_text=before, language='python', verifier=oracle,
               scope_id=scope, context=context, required_verification_kind='TEST_SUITE')
print(json.dumps({'pid': os.getpid(), 'result': result, 'skill_count': store.count(), 'oracle_calls': oracle.calls}))
'''


def child(mode, db, root, target):
    proc = subprocess.run([sys.executable, '-c', CHILD, mode, str(db), str(root), target,
                           SCOPE, json.dumps(CONTRACT)], cwd=ROOT, text=True, capture_output=True, timeout=30)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def test_cross_package_restart_and_causal_artifact_ablations(tmp_path, record_property):
    training, held_out = tmp_path / 'ledger_project', tmp_path / 'workshop_project'
    train_target, _, _ = project(training)
    target, before, after = project(held_out, held_out=True)
    untouched_training, untouched_held = snapshot(training), snapshot(held_out)
    db = tmp_path / 'retained.sqlite'
    baseline = child('baseline', db, held_out, target)
    assert baseline['result']['passed'] is False
    assert baseline['result']['evidence']['test_count'] == 3
    cold = child('recall', db, held_out, target)
    assert cold['result'] is None and cold['skill_count'] == 0
    taught = child('teach', db, training, train_target)
    assert taught['result']['crystallized']
    replay = child('recall', db, held_out, target)
    assert replay['pid'] != taught['pid']
    assert replay['result']['patched_source'] == after
    verification = replay['result']['verification']
    assert verification['kind'] == 'TEST_SUITE'
    assert verification['candidate_sha256'] == source_sha256(after)
    assert verification['evidence']['test_count'] == 3
    assert replay['result']['skill_id'] == taught['result']['skill_id']
    assert replay['result']['whole_task_correctness_proved'] is False
    disabled = child('disabled', db, held_out, target)
    assert disabled['result'] is None and disabled['skill_count'] == 1
    assert disabled['oracle_calls'] == 0
    artifact = db.with_suffix('.retained')
    db.rename(artifact)
    removed = child('recall', db, held_out, target)
    assert removed['result'] is None and removed['skill_count'] == 0
    db.unlink()
    artifact.rename(db)
    restored = child('recall', db, held_out, target)
    assert restored['result']['patched_source'] == after
    assert restored['result']['skill_id'] == replay['result']['skill_id']
    assert snapshot(training) == untouched_training
    assert snapshot(held_out) == untouched_held
    assert (held_out / target).read_text() == before
    record_property('retained_skill_restart_run', json.dumps({
        'baseline': baseline, 'cold': cold, 'taught': taught, 'replay': replay,
        'disabled': disabled, 'removed': removed, 'restored': restored,
        'original_projects_unchanged': True, 'test_files_untouched': True,
        'scope': 'two separately constructed Python package projects; one arithmetic repair pattern',
        'independent_verification': False, 'fallback_search_algorithm': None}))


def test_same_shape_different_behavior_is_rejected_by_current_project_tests(lesson, tmp_path):
    store, _, _, _, _ = lesson
    root = tmp_path / 'subtraction_project'
    target, before, _ = project(root, held_out=True)
    tests = root / 'test_behavior.py'
    tests.write_text(tests.read_text().replace('],7),29)', '],7),15)').replace('],-4),11)', '],-4),19)'))
    untouched = snapshot(root)
    oracle = ProjectTestOracle(root, target, ['test_behavior.py'], SCOPE)
    assert oracle(before).passed is True
    assert recall(store, before, oracle) is None
    assert snapshot(root) == untouched


@pytest.mark.parametrize('target', ['./test_behavior.py', 'test_behavior.py'])
def test_test_path_aliases_cannot_bypass_rewrite_refusal(tmp_path, target):
    root = tmp_path / 'project'
    project(root)
    with pytest.raises(ValueError, match='MUST_NOT_REWRITE_ITS_TESTS'):
        ProjectTestOracle(root, target, ['test_behavior.py'], SCOPE)


def test_failing_typed_twin_result_is_not_truthy_success(tmp_path):
    store = VerifiedSkillStore(tmp_path / 'skills.sqlite', seed=False)
    def reject(source):
        return VerificationResult(False, 'SYNTAX', source_sha256(source))
    result = store.crystallize_code_fix(before_snippet='def f(a,b): return a-b',
                                        after_snippet='def f(a,b): return a+b', language='python', twin_oracle=reject)
    assert result == {'crystallized': False, 'reason': 'FAILED_MUTATED_TWIN_VERIFICATION'}
    assert store.count() == 0


def test_unknown_contract_constraints_are_not_silently_dropped(tmp_path):
    root = tmp_path / 'project'
    target, before, after = project(root)
    store = VerifiedSkillStore(tmp_path / 'skills.sqlite', seed=False)
    with pytest.raises(ValueError, match='UNSUPPORTED_SKILL_CONTRACT_FIELD'):
        store.crystallize_code_fix(before_snippet=before, after_snippet=after, language='python',
                                   contract={**CONTRACT, 'unimplemented_security_condition': True},
                                   training_verifier=ProjectTestOracle(root, target, ['test_behavior.py'], SCOPE))


def test_scoped_bundle_round_trip_preserves_identity_and_invalidation(lesson, tmp_path):
    store, oracle, before, _, result = lesson
    active_bundle = store.export_bundle()
    consumer = VerifiedSkillStore(tmp_path / 'consumer.sqlite', seed=False)
    assert consumer.import_bundle(active_bundle)['accepted'] == 1
    assert recall(consumer, before, oracle)['skill_id'] == result['skill_id']
    assert store.invalidate(result['skill_id'], 'transported counterexample')
    assert consumer.import_bundle(store.export_bundle())['merged'] == 1
    assert recall(consumer, before, oracle) is None
    assert consumer.lookup_rules('python')[0]['counterexamples'][0]['reason'] == 'transported counterexample'
    assert consumer.import_bundle(active_bundle)['merged'] == 1
    assert recall(consumer, before, oracle) is None
    fresh = VerifiedSkillStore(tmp_path / 'invalidated.sqlite', seed=False)
    assert fresh.import_bundle(consumer.export_bundle())['accepted'] == 1
    assert recall(fresh, before, oracle) is None


def test_tampered_scoped_bundle_contract_is_refused(lesson, tmp_path):
    store, _, _, _, _ = lesson
    bundle = store.export_bundle()
    bundle['rules'][0]['rule']['contract']['scope_id'] = 'tampered-scope'
    consumer = VerifiedSkillStore(tmp_path / 'consumer.sqlite', seed=False)
    result = consumer.import_bundle(bundle)
    assert result['accepted'] == 0
    assert result['refusals'][0]['reason'] == 'CONTENT_ADDRESS_MISMATCH'
    assert consumer.count() == 0

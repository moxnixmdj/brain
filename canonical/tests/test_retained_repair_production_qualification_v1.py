"""Real production application, capable baseline and scoped retained transfer.

No subprocess/import/filesystem substitution. External project snapshots are
licensed, pinned files; faults and acceptance/audit tests are authored here.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import py_compile
import sys

import pytest

from canonical.runtime.bound_capabilities import python_repair_apply_verified_v1 as apply
from canonical.swe_kernel import verified_skill_crystallizer_v1 as skills
from canonical.tests.retained_repair_curriculum_v1 import (
    FIXTURES, FAMILIES, audit, build_case, execute,
)


def simple_project(tmp_path, test_source=None):
    root = tmp_path / 'project'
    root.mkdir()
    target = root / 'm.py'
    target.write_text('def add(a,b): return a-b\n')
    test = root / 'test_m.py'
    test.write_text(test_source or (
        'import unittest\nfrom m import add\n'
        'class Tests(unittest.TestCase):\n def test_add(self): self.assertEqual(add(2,3),5)\n'))
    args = {'source_root': '.', 'test_paths': ['test_m.py'],
            'output_path': 'report.json', 'timeout_s': 20}
    return root, target, test, args


def test_a_command_that_mentions_tests_without_executing_them_cannot_authorize_success(tmp_path):
    root, target, test, args = simple_project(tmp_path)
    original = target.read_bytes(), test.read_bytes()
    args['test_argv'] = [sys.executable, '-c', 'pass', 'test_m.py']
    result = apply.run(args, root)
    assert result['pass'] is False
    assert result['applied'] is False
    assert result['status'] == 'FAIL_CLOSED__STATED_COMMAND_AND_DECLARED_CORPUS_DISAGREE'
    assert result['pre_apply_test_returncode'] == 0
    assert result['pre_apply_corpus']['returncode'] != 0
    assert result['pre_apply_corpus']['observed_test_count'] == 1
    assert (target.read_bytes(), test.read_bytes()) == original


@pytest.mark.parametrize('source', [
    'import unittest\n',
    'import unittest\n@unittest.skip("not implemented")\nclass Tests(unittest.TestCase):\n def test_skip(self): self.fail()\n',
])
def test_empty_or_all_skipped_corpus_never_becomes_already_satisfied(tmp_path, source):
    root, target, _, args = simple_project(tmp_path, source)
    before = target.read_bytes()
    args['test_argv'] = [sys.executable, '-c', 'pass', 'test_m.py']
    result = apply.run(args, root)
    assert result['pass'] is False
    assert result['applied'] is False
    assert target.read_bytes() == before


def test_already_correct_source_is_checked_without_reading_stale_bytecode(tmp_path):
    root, target, test, args = simple_project(tmp_path)
    py_compile.compile(str(target), doraise=True)
    stat = target.stat()
    target.write_text('def add(a,b): return a+b\n')
    os.utime(target, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    result = apply.run(args, root)
    assert result['pass'] is True
    assert result['already_satisfied'] is True
    assert result['applied'] is False
    assert result['pre_apply_corpus']['observed_test_count'] == 1
    assert target.read_text() == 'def add(a,b): return a+b\n'


def test_self_modifying_declared_tests_are_restored_and_refused(tmp_path):
    source = ('import unittest\nfrom pathlib import Path\nfrom m import add\n'
              'class Tests(unittest.TestCase):\n'
              ' def test_add(self):\n'
              '  p=Path(__file__); p.write_text(p.read_text()+"\\n")\n'
              '  self.assertEqual(add(2,3),5)\n')
    root, target, test, args = simple_project(tmp_path, source)
    before = target.read_bytes(), test.read_bytes()
    result = apply.run(args, root)
    assert result['pass'] is False
    assert result['status'] == 'FAIL_CLOSED__DECLARED_TESTS_CHANGED_DURING_BASELINE'
    assert (target.read_bytes(), test.read_bytes()) == before


def test_python_twin_uses_real_tokens_and_preserves_literals_and_comments():
    source = ('# value and assert are not names in this comment\n'
              'def encode(value):\n'
              '    assert value >= 1e-10\n'
              '    payload = b"value"; text = r"value"\n'
              '    return value - 1\n')
    twin, names = skills._alpha_mutate_snippet(source)
    ast.parse(twin)
    assert 'value' in names
    assert names['value'] in twin
    assert 'assert ' in twin and '1e-10' in twin
    assert 'b"value"' in twin and 'r"value"' in twin
    assert twin.splitlines()[0] == source.splitlines()[0]


def test_external_source_snapshots_match_their_pinned_manifest():
    manifest = json.loads((FIXTURES / 'PROVENANCE.json').read_text())
    assert len({row['repository'] for row in manifest['fixtures']}) == 3
    for row in manifest['fixtures']:
        assert hashlib.sha256((FIXTURES / row['local_file']).read_bytes()).hexdigest() == row['sha256']
        assert len(row['commit']) == 40
        assert row['commit'] in row['source_url']
        assert (FIXTURES / row['license_file']).stat().st_size > 100


@pytest.mark.parametrize('trial', range(3))
@pytest.mark.parametrize('family', FAMILIES)
def test_retained_transfer_competes_with_actual_search_and_passes_external_audit(tmp_path, family, trial, record_property):
    repo = tmp_path / family
    teaching = build_case(repo, family, 'teaching')
    frozen_teach = teaching['target'].read_bytes(), teaching['test'].read_bytes()
    taught = execute('teach', repo, teaching)
    learnable = family != 'integer_encoding'
    if learnable:
        assert taught['result']['crystallized'], taught
    else:
        # Incoming main pins removed names instead of teaching unsafe API renames.
        assert taught['result']['crystallized'] is False
        assert taught['result']['reason'] == 'FAILED_MUTATED_TWIN_VERIFICATION'
    assert (teaching['target'].read_bytes(), teaching['test'].read_bytes()) == frozen_teach
    baseline = build_case(repo, family, 'baseline')
    baseline['args']['retained_learning']['enabled'] = False
    learned = build_case(repo, family, 'learned')
    original_baseline = baseline['target'].read_bytes()
    frozen_baseline = baseline['test'].read_bytes(), baseline['audit'].read_bytes()
    frozen_learned = learned['test'].read_bytes(), learned['audit'].read_bytes()
    cold = execute('apply', repo, baseline)
    warm = execute('apply', repo, learned)
    assert cold['result']['repair_search_invocations'] == 1  # not a no-fallback baseline
    assert cold['result']['retained_learning']['enabled'] is False
    assert warm['pid'] != taught['pid'] and warm['pid'] != cold['pid']
    if learnable:
        assert warm['result']['pass'] is True and warm['result']['applied'] is True
        assert warm['result']['repair_search_invocations'] == 0
        assert warm['result']['retained_learning']['hit'] is True
        assert warm['result']['post_apply_corpus']['observed_test_count'] == 3
        assert warm['result']['applied_source_sha256'][learned['args']['retained_learning']['target_path']] == hashlib.sha256(learned['target'].read_bytes()).hexdigest()
        warm_audit = audit(learned)
        assert warm_audit['returncode'] == 0, warm_audit
    else:
        assert warm['result']['retained_learning']['hit'] is False
        assert warm['result']['repair_search_invocations'] == 1
        assert warm['result']['pass'] is True
        assert warm['result']['applied'] is True
        assert skills.VerifiedSkillStore(repo / 'memory/skills.sqlite', seed=False).count() == 0
        warm_audit = audit(learned)
        assert warm_audit['returncode'] == 0, warm_audit
    if cold['result']['pass']:
        cold_audit = audit(baseline)
        assert cold_audit['returncode'] == 0, cold_audit
    else:
        cold_audit = audit(baseline)
        assert baseline['target'].read_bytes() == original_baseline
    assert (baseline['test'].read_bytes(), baseline['audit'].read_bytes()) == frozen_baseline
    assert (learned['test'].read_bytes(), learned['audit'].read_bytes()) == frozen_learned
    record_property('retained_production_run', json.dumps({
        'family': family, 'trial': trial, 'learning_expected': learnable, 'teaching': taught, 'baseline': cold, 'learned': warm,
        'baseline_external_audit': cold_audit, 'learned_external_audit': warm_audit,
        'tests_unchanged': True, 'expert_teaching_cost_included_separately': True,
        'baseline_has_same_search_and_trace_fallback': True,
        'resource_scope': 'Waited-for child CPU and max single-child RSS, not aggregate process-tree peak',
        'scope': 'Pinned upstream modules with authored seeded defects and tests; not full upstream bug suites',
        'independent_verification': False}))


def test_production_search_can_teach_a_skill_that_next_project_reuses(tmp_path):
    first = build_case(tmp_path, 'floor_boundary', 'first')
    frozen = first['test'].read_bytes()
    result = execute('apply', tmp_path, first)
    assert result['result']['pass'] is True
    assert result['result']['repair_search_invocations'] == 1
    assert result['result']['retained_learning']['teaching']['crystallized'] is True
    second = build_case(tmp_path, 'floor_boundary', 'second')
    replay = execute('apply', tmp_path, second)
    assert replay['result']['retained_learning']['hit'] is True
    assert replay['result']['repair_search_invocations'] == 0
    assert audit(second)['returncode'] == 0
    assert first['test'].read_bytes() == frozen


def test_artifact_removal_and_restoration_keep_actual_search_available(tmp_path):
    teaching = build_case(tmp_path, 'floor_boundary', 'teaching')
    assert execute('teach', tmp_path, teaching)['result']['crystallized']
    db = tmp_path / 'memory/skills.sqlite'
    saved = db.with_suffix('.saved')
    db.rename(saved)
    missing = build_case(tmp_path, 'floor_boundary', 'missing')
    before = missing['target'].read_bytes()
    result = execute('apply', tmp_path, missing)
    assert result['result']['repair_search_invocations'] == 1
    assert result['result']['retained_learning']['hit'] is False
    assert result['result']['pass'] is True
    assert missing['target'].read_bytes() != before
    assert audit(missing)['returncode'] == 0
    db.unlink()
    saved.rename(db)
    restored = build_case(tmp_path, 'floor_boundary', 'restored')
    result = execute('apply', tmp_path, restored)
    assert result['result']['retained_learning']['hit'] is True
    assert result['result']['pass'] is True
    assert audit(restored)['returncode'] == 0


def test_inapplicable_scope_does_not_disable_fresh_search(tmp_path):
    teaching = build_case(tmp_path, 'floor_boundary', 'teaching')
    assert execute('teach', tmp_path, teaching)['result']['crystallized']
    case = build_case(tmp_path, 'floor_boundary', 'incompatible')
    case['args']['retained_learning']['context'] = {'dependencies': {}, 'preconditions': {}}
    result = execute('apply', tmp_path, case)['result']
    assert result['retained_learning']['applicable'] is False
    assert result['retained_learning']['hit'] is False
    assert result['retained_learning']['oracle_calls'] == 0
    assert result['repair_search_invocations'] == 1
    assert result['pass'] is True
    assert audit(case)['returncode'] == 0


def test_invalidated_skill_is_not_applied_by_production_path(tmp_path):
    teaching = build_case(tmp_path, 'floor_boundary', 'teaching')
    taught = execute('teach', tmp_path, teaching)['result']
    store = skills.VerifiedSkillStore(tmp_path / 'memory/skills.sqlite', seed=False)
    assert store.invalidate(taught['skill_id'], 'qualification counterexample')
    case = build_case(tmp_path, 'floor_boundary', 'invalidated')
    result = execute('apply', tmp_path, case)['result']
    assert result['retained_learning']['hit'] is False
    assert result['repair_search_invocations'] == 1
    assert result['pass'] is True
    assert audit(case)['returncode'] == 0
    invalidated = [rule for rule in store.lookup_rules('python') if rule['skill_id'] == taught['skill_id']]
    assert len(invalidated) == 1
    assert invalidated[0]['state'] == 'INVALIDATED'


def test_passing_stated_command_cannot_authorize_a_patch_that_fails_the_corpus(tmp_path):
    source = ('import unittest\nfrom m import add\nclass Tests(unittest.TestCase):\n'
              ' def test_multiply(self): self.assertEqual(add(2,3),6)\n')
    root, target, test, args = simple_project(tmp_path, source)
    before = target.read_bytes(), test.read_bytes()
    command = "import pathlib; assert 'a+b' in pathlib.Path('m.py').read_text().replace(' ','')"
    args.update(test_argv=[sys.executable, '-c', command, 'test_m.py'], mutations_per_file=12, max_pair_candidates=8)
    result = apply.run(args, root)
    assert result['post_apply_test_returncode'] == 0  # command alone would approve the wrong patch
    assert result['post_apply_corpus']['returncode'] != 0
    assert result['status'] == 'FAIL_CLOSED__IN_PLACE_VERIFICATION_FAILED_AFTER_APPLY'
    assert result['pass'] is False and result['applied'] is False
    assert (target.read_bytes(), test.read_bytes()) == before


def test_generated_regression_is_verified_and_final_source_hash_matches(tmp_path):
    root, target, test, args = simple_project(tmp_path)
    original_test = test.read_bytes()
    target.chmod(0o754)
    args['synthesize_regression_test'] = True
    result = apply.run(args, root)
    assert result['pass'] is True
    assert result['generated_regression_verification']['returncode'] == 0
    assert result['generated_regression_verification']['observed_test_count'] == 2
    assert result['applied_source_sha256']['m.py'] == hashlib.sha256(target.read_bytes()).hexdigest()
    assert test.read_bytes() == original_test
    assert target.stat().st_mode & 0o777 == 0o754


def test_regression_generation_never_overwrites_an_existing_test(tmp_path):
    root, target, test, args = simple_project(tmp_path)
    prior = root / 'test_regression_m_add.py'
    prior.write_text('# existing user test, not a generated artifact to replace\n')
    frozen = target.read_bytes(), test.read_bytes(), prior.read_bytes()
    args['synthesize_regression_test'] = True
    with pytest.raises(apply.RepairApplyError, match='REGRESSION_TEST_DESTINATION_ALREADY_EXISTS'):
        apply.run(args, root)
    assert (target.read_bytes(), test.read_bytes(), prior.read_bytes()) == frozen


def test_corrupt_retention_falls_back_without_destroying_the_artifact(tmp_path):
    case = build_case(tmp_path, 'floor_boundary', 'corrupt_memory')
    db = tmp_path / 'memory/skills.sqlite'
    db.parent.mkdir()
    original = b'not a sqlite database'
    db.write_bytes(original)
    result = execute('apply', tmp_path, case)['result']
    assert result['pass'] is True
    assert result['retained_learning']['hit'] is False
    assert result['retained_learning']['retention_error'] == 'DatabaseError'
    assert result['repair_search_invocations'] == 1
    assert db.read_bytes() == original  # do not silently erase failed retained state
    assert audit(case)['returncode'] == 0


def test_atomic_source_write_does_not_clobber_an_existing_temp_sibling(tmp_path):
    target = tmp_path / 'm.py'
    target.write_bytes(b'old')
    target.chmod(0o751)
    sibling = tmp_path / 'm.py.brain_apply_tmp'
    sibling.write_bytes(b'unrelated data')
    apply._atomic_write(target, b'new')
    assert target.read_bytes() == b'new'
    assert target.stat().st_mode & 0o777 == 0o751
    assert sibling.read_bytes() == b'unrelated data'
    assert [p.name for p in tmp_path.iterdir() if p.name.startswith('m.py.brain_apply_')] == [sibling.name]


def test_retained_repair_also_works_when_source_root_is_the_repository(tmp_path):
    root, target, _, args = simple_project(tmp_path)
    contract = {'schema_version': 1, 'scope_id': 'root-project/add/v1',
                'verification_kind': 'TEST_SUITE', 'dependencies': {},
                'preconditions': {'operation': 'addition'}}
    args['retained_learning'] = {'enabled': True, 'db_path': 'memory/skills.sqlite',
        'target_path': 'm.py', 'contract': contract,
        'context': {'dependencies': {}, 'preconditions': {'operation': 'addition'}}}
    first = apply.run(args, root)
    assert first['pass'] is True
    assert first['retained_learning']['teaching']['crystallized'] is True
    target.write_text('def add(a,b): return a-b\n')
    replay = apply.run(args, root)
    assert replay['pass'] is True
    assert replay['retained_learning']['hit'] is True
    assert replay['repair_search_invocations'] == 0


def test_real_bound_dispatcher_can_teach_then_recall_without_search():
    import tempfile
    from canonical.runtime import astra_runtime
    root = Path(__file__).resolve().parents[2]
    scratch = root / 'canonical/astra_runtime/tmp'
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='retained_bound_', dir=scratch) as td:
        project, target, _, args = simple_project(Path(td))
        rel = project.relative_to(root).as_posix()
        args.update(capability_id='python.software.repair.apply.verified.v1',
                    source_root=rel, test_paths=[rel + '/test_m.py'],
                    output_path=rel + '/repair.json')
        args['retained_learning'] = {
            'enabled': True, 'target_path': rel + '/m.py',
            'db_path': str(Path(td).relative_to(root) / 'memory.sqlite'),
            'contract': {'schema_version': 1, 'scope_id': 'bound/add/v1',
                         'verification_kind': 'TEST_SUITE',
                         'dependencies': {}, 'preconditions': {}},
            'context': {'dependencies': {}, 'preconditions': {}}}
        taught = astra_runtime._invoke_bound_capability(args)
        assert taught['pass'] is True
        assert taught['retained_learning']['teaching']['crystallized'] is True
        target.write_text('def add(a,b): return a-b\n')
        replay = astra_runtime._invoke_bound_capability(args)
        assert replay['pass'] is True
        assert replay['retained_learning']['hit'] is True
        assert replay['repair_search_invocations'] == 0
        assert replay['applied_source_sha256']['%s/m.py' % rel] == hashlib.sha256(target.read_bytes()).hexdigest()


def test_unavailable_retention_directory_does_not_block_capable_fallback(tmp_path):
    case = build_case(tmp_path, 'floor_boundary', 'unavailable_memory')
    blocked = tmp_path / 'memory'
    blocked.write_bytes(b'preserve this unrelated file')
    result = execute('apply', tmp_path, case)['result']
    assert result['pass'] is True
    assert result['repair_search_invocations'] == 1
    assert result['retained_learning']['hit'] is False
    assert result['retained_learning']['retention_error'] == 'FileExistsError'
    assert blocked.read_bytes() == b'preserve this unrelated file'
    assert audit(case)['returncode'] == 0
